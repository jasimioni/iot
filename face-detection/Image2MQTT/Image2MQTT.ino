#include <WiFi.h>
#include <PubSubClient.h>
#include "esp_camera.h"
#include "board_config.h"
#include "fb_gfx.h"
#include "img_converters.h"
#include "human_face_detect_msr01.hpp" 

// ================= CONFIGURATION =================
const char *ssid = "";
const char *password = "";

const char* mqtt_server = ""; 
const char* mqtt_user = ""; 
const char* mqtt_pass = "";
const char* mqtt_topic = "esp32/cam/image";
const char* mqtt_topic_cmd = "esp32/cam/cmd";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

HumanFaceDetectMSR01 detector(0.3F, 0.3F, 10, 0.3F);

bool only_send_if_face_detected = false;
bool disable_send = true;

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");

  // 1. Convert payload to a String safely
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.printf("################################## %s", message);

  if (message == "enable_only_send_if_face_detected") {
    only_send_if_face_detected = true;
    Serial.println("################################# Enabled only_send_if_face_detected");

  } else if (message == "disable_only_send_if_face_detected") {
    only_send_if_face_detected = false;
    Serial.println("################################# Disabled only_send_if_face_detected");
  } else if (message == "disable") {
    disable_send = true;
  } else if (message == "enable") {
    disable_send = false;
  }
}


void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);

  // 1. Initialize Camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Resolution: Keep it low to ensure it fits in MQTT buffer
  config.frame_size = FRAMESIZE_QVGA; // 320x240
  config.jpeg_quality = 12; // 0-63 lower number means higher quality
  config.fb_count = 1;

  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // 2. Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // 3. Configure MQTT
  client.setServer(mqtt_server, mqtt_port);
  
  // CRITICAL: Increase buffer size to handle image data (e.g., 20KB)
  // Standard buffer is only 256 bytes.
  client.setBufferSize(8000); 
  client.setCallback(callback); // Register the listening function

}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32CamClient", mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      client.subscribe(mqtt_topic_cmd);
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic_cmd);      
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

void swapBytes(uint16_t * imgBuffer, size_t pixelCount) {
  // We use uint32_t pointer to swap 2 pixels at a time (Optimization)
  // This makes it 2x faster than iterating pixel by pixel
  uint32_t *ptr = (uint32_t *)imgBuffer;
  size_t count = pixelCount / 2;
  
  for (size_t i = 0; i < count; i++) {
    // __builtin_bswap16 is slow loop-wise, but we can use bswap32 with logic
    // Or simpler: just standard loop with compiler intrinsic optimization
    uint32_t val = ptr[i];
    // Swap bytes inside the 32-bit word for two 16-bit pixels
    // AABB CCDD -> BBAA DDCC
    ptr[i] = ((val & 0x00FF00FF) << 8) | ((val & 0xFF00FF00) >> 8);
  }
}

void captureAndSend() {
  // A. Take Picture
  if (disable_send)
    return;

  camera_fb_t * fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Camera capture failed");
    return;
  }

  Serial.printf("Picture taken! Size: %d bytes\n", fb->len);

  bool publish = true;

  if (only_send_if_face_detected) {
    Serial.printf("Converting to rgb (%d, %d)\n", fb->height, fb->width);

    uint16_t *rgb_buffer = (uint16_t *)ps_malloc(320 * 240 * sizeof(uint16_t));
    bool success = jpg2rgb565(fb->buf, fb->len, (uint8_t *) rgb_buffer, JPG_SCALE_NONE);   
    Serial.printf("Converting completed - Detecting\n");

    swapBytes(rgb_buffer, fb->width * fb->height);

    auto &detection_results = detector.infer(rgb_buffer, {(int)fb->height, (int)fb->width, 3});
    free(rgb_buffer);


    Serial.printf("Detecting process completed\n");

    if (detection_results.size() > 0) {
      Serial.printf("Rostos detectados: %d\n", detection_results.size());
    
      // Desenhar quadrado em cada rosto encontrado
      for (auto &result : detection_results) {
        // Coordenadas do quadrado (Box)
        int x = (int)result.box[0];
        int y = (int)result.box[1];
        int w = (int)result.box[2] - x + 1; // width
        int h = (int)result.box[3] - y + 1; // height
        float score = result.score;

        Serial.printf("Face: x=%d, y=%d, w=%d, h=%d, conf=%.2f\n", x, y, w, h, score);
      }
    } else {
      publish = false;
      Serial.printf("No faces detected\n");
    }
  }

  if (publish) {
    // B. Check if image fits in buffer
    if (fb->len > 8000) {
      Serial.println("Image too large for MQTT buffer!");
    } else {
      // C. Publish the raw bytes
      if (client.publish(mqtt_topic, (const uint8_t*)fb->buf, fb->len, false)) {
        Serial.println("Image published successfully!");
      } else {
         Serial.println("Publish failed.");
      }
    }
  } else {

  }

  // D. Return the frame buffer to memory
  esp_camera_fb_return(fb);
}

void loop() {
  if (!client.connected()) {
     reconnect();
  }
  client.loop();

  // Take and send a photo every 10 seconds
  captureAndSend();
}
