/*
  Deep Sleep with External Wake Up
  =====================================
  This code displays how to use deep sleep with
  an external trigger as a wake up source and how
  to store data in RTC memory to use it over reboots

  This code is under Public Domain License.

  Hardware Connections
  ======================
  Push Button to GPIO 33 pulled down with a 10K Ohm
  resistor

  NOTE:
  ======
  Only RTC IO can be used as a source for external wake
  source. They are pins: 0,2,4,12-15,25-27,32-39.

  Author:
  Pranav Cherukupalli <cherukupallip@gmail.com>
*/
#include "esp_camera.h"
#include <Arduino.h>
#include "driver/rtc_io.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include "time.h"
#include <Vector.h>
//#include <ArduinoJson.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"


RTC_DATA_ATTR int bootCount = 0;

// CAMERA
#define CAMERA_MODEL_AI_THINKER
#if defined(CAMERA_MODEL_AI_THINKER)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#else
#error "Camera model not selected"
#endif

// TIME
#define TIMEZONE "WIB-7";
const char* NTPSERVER = "pool.ntp.org";
const int dayOffset_sec = 3600;

// WIFI
const char *ssid = "Yfi";
const char *pass = "qweasdzxc21";

// MQTT BROKER
const char *broker_address = "192.168.51.119";
const int port = 1883;
const char *topicTime = "edge/cam/1/time";
const char *topicProgress = "edge/cam/1/inprogress";
const char *topicDone = "edge/cam/1/done";


WiFiClient espClient;
PubSubClient client(espClient);
camera_config_t config;


String getTimeNow() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("fail");
  }
  Serial.println(&timeinfo, "%H:%M:%S");
  char time_[20];
  strftime(time_, 20, "%H:%M:%S", &timeinfo);
  String str(time_);
  return str;
}

void print_wakeup_reason() {
  esp_sleep_wakeup_cause_t wakeup_reason;

  wakeup_reason = esp_sleep_get_wakeup_cause();

  switch (wakeup_reason)
  {
    case ESP_SLEEP_WAKEUP_EXT0 : Serial.println("Wakeup caused by external signal using RTC_IO"); break;
    case ESP_SLEEP_WAKEUP_EXT1 : Serial.println("Wakeup caused by external signal using RTC_CNTL"); break;
    default : Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason); break;
  }
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  delay(500); //Take some time to open up the Serial Monitor
  WiFi.disconnect();
  //Increment boot number and print it every reboot
  ++bootCount;
  Serial.println("Boot number: " + String(bootCount));

  //Print the wakeup reason for ESP32
  print_wakeup_reason();
  pinMode(GPIO_NUM_13, INPUT_PULLUP);
  setup_camera();


  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_EXT0) {
    WiFi.begin(ssid, pass);
    Serial.println("Connecting to wifi");
    while (WiFi.status() != WL_CONNECTED) {
      delay(200);
      Serial.print(".");
    }
    Serial.println();

    String client_id = "esp32-client-";
    client.setServer(broker_address, port);
    delay(100);

    while (!client.connected()) {
      client_id += String(WiFi.macAddress());
      Serial.println("Client connect to " + client_id);
      configTime(0, dayOffset_sec, NTPSERVER);
      setenv("TZ", "WIB-7", 1);
      tzset();
      if (client.connect(client_id.c_str())) {
        Serial.println("Client Connected");
        //        client.publish(topic, (const char*)fb->buf);

        Serial.println("tt");
        // CHANGE THE FOR CONDITION TO INCREASE IMAGE TAKEN
        for (int i = 0; i <= 11; i++) {
          pinMode(4, OUTPUT);
          digitalWrite(4, LOW);
          camera_fb_t *fb = NULL;
          fb = esp_camera_fb_get();
          if (i <= 5) {
            esp_camera_fb_return(fb);
            continue;
          }
          delay(200);
          // GET TIME USING NTP SERVER
          //          String timeNow = getTimeNow();
          String timeNow = "img_gen_mode";
          Serial.println("asd");
          if (!fb) {
            Serial.println("Camera capture failed");
            delay(1000);
            ESP.restart();
          }

          client.setBufferSize(4096 + 60);
          byte s_array[4100];
          Vector<byte> vector(s_array);
          Serial.println("properties img =====");
          Serial.println(fb->len);
          Serial.println(fb->width);
          Serial.println(fb->height);
          Serial.println("======");
          if (client.publish(topicTime, timeNow.c_str())) {
            Serial.println("time published");
            Serial.println("====");
            delay(200);
          }
          //        if (client.publish(topicDone, fb->buf, fb->len)) {
          //          Serial.println("published");
          //          delay(300);
          //        }

          for (int j = 0; j < fb->len; j++) {
            vector.push_back(fb->buf[j]);

            if (j == fb->len - 1) {
              //            Serial.println(vector.size());
              if (client.publish(topicDone, vector.data(), vector.size(), false)) {
                Serial.println("All part of data published");
              }
              delay(100);
              vector.clear();
            }
            //           if (j % 128 == 0 && j != 0)
            else if (j % 4096 == 0 && j != 0) {
              if (client.publish(topicProgress, vector.data(), vector.size(), false)) {
                //              Serial.println("Next part of data begin to publish");
              }
              delay(100);
              vector.clear();
            }

          }

          esp_camera_fb_return(fb);
          delay(200);
        }
      }
      else {
        Serial.printf("Failed with state %d \n", client.state());
        delay(2000);
      }

    }
    client.disconnect();

  }

  //If you were to use ext1, you would use it like
  //esp_sleep_enable_ext1_wakeup(BUTTON_PIN_BITMASK,ESP_EXT1_WAKEUP_ANY_HIGH);

  //  rtc_gpio_hold_en(GPIO_NUM_4);


  //Go to sleep now
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_13, HIGH); //1 = High, 0 = Low
  Serial.println("Going to sleep now");
  delay(2000);

  esp_deep_sleep_start();
  Serial.println("This will never be printed");
}

void setup_camera() {
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
  config.xclk_freq_hz = 16500000;
  //  config.pixel_format = PIXFORMAT_RGB565;
  config.pixel_format = PIXFORMAT_JPEG;

  // init with high specs to pre-allocate larger buffers
  if (psramFound()) {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 6;  //0-63 lower number means higher quality
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
  } else {
    config.frame_size = FRAMESIZE_CIF;
    config.jpeg_quality = 40;  //0-63 lower number means higher quality
    config.fb_count = 1;
  }

  // Initialize the Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 1); // -2 to 2
  s->set_contrast(s, -1); // -2 to 2
  s->set_saturation(s, 0); // -2 to 2
  s->set_special_effect(s, 0); // 0 to 6 (0 - No Effect, 1 - Negative, 2 - Grayscale, 3 - Red Tint, 4 - Green Tint, 5 - Blue Tint, 6 - Sepia)
  s->set_whitebal(s, 1); // 0 = disable , 1 = enable
  s->set_awb_gain(s, 1); // 0 = disable , 1 = enable
  s->set_wb_mode(s, 1); // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
  s->set_exposure_ctrl(s, 1); // 0 = disable , 1 = enable
  s->set_aec2(s, 0); // 0 = disable , 1 = enable
  //  s->set_ae_level(s, 0); // -2 to 2
  //  s->set_aec_value(s, 400); // 0 to 1200
  s->set_gain_ctrl(s, 1); // 0 = disable , 1 = enable
  s->set_agc_gain(s, 0); // 0 to 30
  s->set_gainceiling(s, (gainceiling_t)5); // 0 to 6
  s->set_bpc(s, 1); // 0 = disable , 1 = enable
  s->set_wpc(s, 1); // 0 = disable , 1 = enable
  s->set_raw_gma(s, 1); // 0 = disable , 1 = enable (makes much lighter and noisy)
  s->set_lenc(s, 0); // 0 = disable , 1 = enable
  s->set_hmirror(s, 0); // 0 = disable , 1 = enable
  s->set_vflip(s, 0); // 0 = disable , 1 = enable
  s->set_dcw(s, 0); // 0 = disable , 1 = enable
  s->set_colorbar(s, 0); // 0 = disable , 1 = enable
  //  s->set_reg(s, 0xff, 0xff, 0x01); //banksel
  //  s->set_reg(s, 0x11, 0xff, 01); //frame rate
  //  s->set_reg(s, 0xff, 0xff, 0x00); //banksel
  //  s->set_reg(s, 0x86, 0xff, 1); //disable effects
  //  s->set_reg(s, 0xd3, 0xff, 5); //clock
  //  s->set_reg(s, 0x42, 0xff, 0x4f); //image quality (lower is bad)
  //  s->set_reg(s, 0x44, 0xff, 1); //quality
  Serial.println("wait config");
  delay(700);
  Serial.println("continue");
}

void loop() {
  //This is not going to be called
}
