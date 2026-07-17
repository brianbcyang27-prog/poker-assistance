/*
 * ServoControl.ino — JARVIS IoT servo/actuator control example.
 * 
 * Controls 2 servo motors and an RGB LED strip.
 * JARVIS can send position commands, color changes, and animations.
 *
 * Circuit:
 *   Servo 1 → GPIO 12
 *   Servo 2 → GPIO 13
 *   RGB LED data → GPIO 15 (WS2812B)
 */

#include <JarvisIoT.h>
#include <ESP32Servo.h>
#include <Adafruit_NeoPixel.h>

#define SERVO1_PIN 12
#define SERVO2_PIN 13
#define LED_PIN 15
#define NUM_LEDS 8

Servo servo1;
Servo servo2;
AdaPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

JarvisIoT jarvis(
    "Robot Arm Controller",
    "YOUR_WIFI_SSID",
    "YOUR_WIFI_PASSWORD"
);

void setup() {
    Serial.begin(115200);
    
    servo1.attach(SERVO1_PIN);
    servo2.attach(SERVO2_PIN);
    servo1.write(90);
    servo2.write(90);
    
    strip.begin();
    strip.setBrightness(50);
    strip.show();
    
    jarvis.begin();
    
    // Servo commands
    jarvis.onCommand("servo1", [](JsonDocument& p, JsonDocument& r) {
        int angle = p["angle"] | 90;
        angle = constrain(angle, 0, 180);
        servo1.write(angle);
        r["status"] = "ok";
        r["data"]["servo1"] = angle;
    });
    
    jarvis.onCommand("servo2", [](JsonDocument& p, JsonDocument& r) {
        int angle = p["angle"] | 90;
        angle = constrain(angle, 0, 180);
        servo2.write(angle);
        r["status"] = "ok";
        r["data"]["servo2"] = angle;
    });
    
    jarvis.onCommand("servos", [](JsonDocument& p, JsonDocument& r) {
        int a1 = p["s1"] | 90;
        int a2 = p["s2"] | 90;
        servo1.write(constrain(a1, 0, 180));
        servo2.write(constrain(a2, 0, 180));
        r["status"] = "ok";
        r["data"]["servo1"] = a1;
        r["data"]["servo2"] = a2;
    });
    
    // LED commands
    jarvis.onCommand("led_color", [](JsonDocument& p, JsonDocument& r) {
        uint8_t red = p["r"] | 255;
        uint8_t green = p["g"] | 255;
        uint8_t blue = p["b"] | 255;
        for (int i = 0; i < NUM_LEDS; i++) {
            strip.setPixelColor(i, strip.Color(red, green, blue));
        }
        strip.show();
        r["status"] = "ok";
        r["data"]["color"] = String(red) + "," + String(green) + "," + String(blue);
    });
    
    jarvis.onCommand("led_off", [](JsonDocument& p, JsonDocument& r) {
        for (int i = 0; i < NUM_LEDS; i++) {
            strip.setPixelColor(i, strip.Color(0, 0, 0));
        }
        strip.show();
        r["status"] = "ok";
    });
    
    jarvis.onCommand("home", [](JsonDocument& p, JsonDocument& r) {
        servo1.write(90);
        servo2.write(90);
        r["status"] = "ok";
        r["data"]["message"] = "Servos centered";
    });
    
    jarvis.addActuator("servo1");
    jarvis.addActuator("servo2");
    jarvis.addActuator("led_strip");
    
    jarvis.setMetadata("board", "ESP32");
    jarvis.setMetadata("type", "robot_arm");
    jarvis.setMetadata("servos", "2");
    jarvis.setMetadata("leds", String(NUM_LEDS).c_str());
    
    jarvis.registerWith("192.168.1.100", 8000);
}

void loop() {
    jarvis.update();
}
