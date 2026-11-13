#pragma once

#include <string>
#include "esphome/core/component.h"
#include "esphome/core/gpio.h"
#include "esphome/components/uart/uart.h"

namespace esphome {
namespace roomba_oi {

// Composant ESPHome pour Roomba serie 500/600 (Open Interface, 115200 bauds).
// - lit le flux de capteurs (opcode 148) meme en mode Passive (Roomba qui nettoie seul)
// - calcule la pose (x, y, theta) : encodeurs + gyroscope MPU6050
// - pilotage manuel (Safe + Drive Direct) avec watchdog
// Conventions : x avant, y gauche, theta anti-horaire (0 = orientation du robot sur la base).
// Unites publiees : mm et degres.
class RoombaOI : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_brc_pin(GPIOPin *pin) { brc_pin_ = pin; }
  void set_wall_snap(bool v) { wall_snap_ = v; }
  void set_calibration(float distance_scale, float wheel_base_mm) {
    distance_scale_ = distance_scale;
    wheel_base_mm_ = wheel_base_mm;
  }
  void set_max_speed(int mm_s) { max_speed_ = mm_s < 50 ? 50 : (mm_s > 500 ? 500 : mm_s); }
  void set_gyro_scale(float s) { gyro_scale_ = s; }
  void set_wall_snap_enabled(bool v) { wall_snap_ = v; }
  bool get_wall_snap_enabled() const { return wall_snap_; }

  // entree gyroscope (deg/s autour de l'axe vertical), appelee par le capteur mpu6050
  void set_gyro_z(float dps);

  // --- commandes ---
  void start_clean() { command_(135); }
  void start_max() { command_(136); }
  void start_spot() { command_(134); }
  void dock() { command_(143); }
  void power_off() { command_(133); }
  void wake();
  void stop();
  void locate();
  void manual_mode(bool on);
  void drive(int left_mm_s, int right_mm_s);         // Drive Direct
  void drive_xy(float forward, float turn);          // -1..1 ; turn>0 = tourne a gauche
  void reset_pose();
  // Reset (opcode 7) : le robot imprime son message de demarrage ; on en extrait « release-... ».
  void read_version();
  std::string get_fw_version() const { return fw_version_; }

  // --- etat ---
  bool stream_ok() const;
  bool is_manual() const { return manual_; }
  bool is_docked() const { return (sources_ & 0x02) != 0; }
  bool is_charging() const { return charge_state_ >= 1 && charge_state_ <= 3; }
  int get_mode() const { return mode_; }
  float get_voltage() const { return voltage_mv_ / 1000.0f; }
  float get_current() const { return current_ma_; }
  float get_battery_pct() const;
  float get_temperature() const { return temp_c_; }
  int get_charge_state() const { return charge_state_; }
  uint8_t get_bumps() const { return bumps_; }
  uint8_t get_wheeldrops() const { return wheeldrops_; }
  uint8_t get_cliffs() const { return cliffs_; }
  float get_x() const { return x_mm_; }
  float get_y() const { return y_mm_; }
  float get_theta_deg() const { return theta_ * 57.29578f; }
  float get_distance_m() const { return odo_total_mm_ / 1000.0f; }
  uint32_t get_bump_count() const { return bump_count_; }
  float get_bump_x() const { return bump_x_; }
  float get_bump_y() const { return bump_y_; }
  float get_bump_theta_deg() const { return bump_theta_ * 57.29578f; }
  int get_bump_side() const { return bump_side_; }
  uint32_t get_snap_count() const { return snap_count_; }
  float get_gyro_bias() const { return gyro_bias_; }
  std::string get_activity() const;
  std::string get_charge_text() const;

 protected:
  void init_();
  void pulse_brc_();
  void command_(uint8_t opcode);
  void send_drive_(int l, int r);
  void feed_(uint8_t b);
  void handle_frame_(const uint8_t *p, uint8_t len);
  void update_pose_(uint16_t enc_l, uint16_t enc_r, uint32_t now);

  GPIOPin *brc_pin_{nullptr};
  bool wall_snap_{true};
  float distance_scale_{1.0f};
  float wheel_base_mm_{235.0f};
  int max_speed_{200};
  float gyro_scale_{1.0f};

  // parseur
  uint8_t buf_[64];
  uint8_t pos_{0};
  uint8_t expect_{0};
  uint8_t state_{0};  // 0 sync, 1 len, 2 body

  // capteurs
  uint8_t bumps_{0}, wheeldrops_{0}, cliffs_{0}, sources_{0}, charge_state_{0}, mode_{0};
  uint16_t voltage_mv_{0}, charge_mah_{0}, capacity_mah_{0};
  int16_t current_ma_{0};
  int8_t temp_c_{0};

  // pose
  bool enc_init_{false};
  uint16_t enc_l_{0}, enc_r_{0};
  float x_mm_{0}, y_mm_{0}, theta_{0};
  float odo_total_mm_{0};
  uint32_t last_pose_ms_{0};
  float gyro_dps_{0}, gyro_bias_{0};
  uint32_t gyro_ms_{0};
  int still_frames_{0};
  bool dock_reset_done_{false};
  uint32_t snap_count_{0};
  uint32_t bump_count_{0};
  float bump_x_{0}, bump_y_{0}, bump_theta_{0};
  int bump_side_{0};
  uint8_t last_bumps_{0};

  // lecture de version
  bool capturing_{false};
  uint32_t capture_start_{0};
  std::string ver_buf_;
  std::string fw_version_{"inconnu"};

  // pilotage / cycle de vie
  bool manual_{false};
  bool returning_{false};
  uint32_t manual_since_{0};
  uint32_t last_drive_ms_{0};
  int cmd_l_{0}, cmd_r_{0};
  uint32_t last_frame_ms_{0};
  uint32_t last_init_ms_{0};
  uint32_t last_keepalive_ms_{0};
};

}  // namespace roomba_oi
}  // namespace esphome
