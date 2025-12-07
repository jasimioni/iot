/*******************************************************************************
* Master Kit - Liquid Crystal Display LCD
* Primeiros passos com um display LCD 16x2.
*******************************************************************************/

#include <LiquidCrystal.h> // inclui a biblioteca para uso do Display LCD
#include <WiFi.h>
#include <PubSubClient.h>

// ================= CONFIGURATION =================
const char *ssid = "";
const char *password = "";

const char* mqtt_server = ""; 
const char* mqtt_user = ""; 
const char* mqtt_pass = "";
const char* mqtt_topic = "esp32/cam/whois";
const int mqtt_port = 1883;
const int RS = 33, EN = 25, D4 = 26, D5 = 27, D6 = 14, D7 = 12;
LiquidCrystal lcd(RS, EN, D4, D5, D6, D7);

WiFiClient espClient;
PubSubClient client(espClient);

void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("]: ");

  // 1. Convert payload to a String safely
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  
  Serial.println(message);

  lcd.clear();
  lcd.setCursor(0, 1); // (coluna 0, linha 1)
  lcd.print(message);
}

void setup(){
  Serial.begin(115200);
  setup_wifi();
  lcd.begin(16, 2); // 16 colunas e 2 linhas
  lcd.clear();
  lcd.setCursor(0, 0); // (coluna 0, linha 0)
  lcd.print("PPGIA - IoT FINAL WORK"); // Imprime mensagem
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback); // Register the listening function
}

void loop(){
  // Calcula o tempo decorrido em segundos desde que o Arduino foi iniciado

  if (!client.connected()) {
    reconnect();
  }
  client.loop(); // Keeps the connection alive and checks for incoming messages  

  delay(500);
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Create a random client ID
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    // Attempt to connect
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("connected");
      
      // *** CRITICAL: Subscribe to the topic here ***
      client.subscribe(mqtt_topic);
      Serial.print("Subscribed to: ");
      Serial.println(mqtt_topic);
      
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}