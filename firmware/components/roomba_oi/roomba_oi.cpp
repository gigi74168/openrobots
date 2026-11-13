#include "roomba_oi.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace roomba_oi {

static const char *const TAG = "roomba_oi";

// Paquets demandes dans le flux (opcode 148). Total des donnees = 38 octets.
static const uint8_t STREAM_IDS[] = {7, 9, 10, 11, 12, 18, 21, 22, 23, 24, 25, 26, 34, 35, 43, 44};

static const float MM_PER_COUNT = 3.14159265f * 72.0f / 508.8f;  // ~0,4445 mm
static const float DEG2RAD = 0.017453293f;
static const float HALF_PI = 1.57079633f;
static const float PI_F = 3.14159265f;

static float wrap_pi(float a) {
  while (a > PI_F) a -= 2 * PI_F;
  while (a < -PI_F) a += 2 * PI_F;
  return a;
}

static uint8_t pkt_len(uint8_t id) {
  switch (id) {
    case 22: case 23: case 25: case 26: case 43: case 44:
      return 2;
    default:
      return 1;
  }
}

void RoombaOI::setup() {
  if (brc_pin_ != nullptr) {
    brc_pin_->setup();
    brc_pin_->digital_write(false);  // transistor bloque : BRC au repos
  }
  last_frame_ms_ = 0;
  last_init_ms_ = millis();
  // laisser le temps au robot, puis init
  this->set_timeout("boot_init", 1500, [this]() {
    this->pulse_brc_();
    this->set_timeout("boot_init2", 300, [this]() { this->init_(); });
  });
}

void RoombaOI::dump_config() {
  ESP_LOGCONFIG(TAG, "Roomba OI");
  LOG_PIN("  BRC pin: ", brc_pin_);
  ESP_LOGCONFIG(TAG, "  Wall snap: %s", wall_snap_ ? "yes" : "no");
  ESP_LOGCONFIG(TAG, "  Wheel base: %.1f mm, distance scale: %.4f", wheel_base_mm_, distance_scale_);
}

void RoombaOI::init_() {
  last_init_ms_ = millis();
  this->write_byte(128);  // START -> Passive
  this->set_timeout("stream_cfg", 60, [this]() {
    uint8_t cmd[2 + sizeof(STREAM_IDS)];
    cmd[0] = 148;
    cmd[1] = sizeof(STREAM_IDS);
    memcpy(cmd + 2, STREAM_IDS, sizeof(STREAM_IDS));
    this->write_array(cmd, sizeof(cmd));
  });
}

void RoombaOI::pulse_brc_() {
  if (brc_pin_ == nullptr) return;
  brc_pin_->digital_write(true);  // transistor passant -> BRC a 0 V
  this->set_timeout("brc_release", 120, [this]() { this->brc_pin_->digital_write(false); });
}

bool RoombaOI::stream_ok() const { return last_frame_ms_ != 0 && (millis() - last_frame_ms_) < 1500; }

void RoombaOI::wake() {
  this->pulse_brc_();
  this->set_timeout("wake_init", 300, [this]() { this->init_(); });
}

void RoombaOI::loop() {
  // 1) lecture du flux
  int budget = 128;
  while (this->available() && budget-- > 0) {
    uint8_t b;
    if (!this->read_byte(&b)) break;
    feed_(b);
  }

  uint32_t now = millis();

  // 1b) fin de capture du message de demarrage (lecture de version)
  if (capturing_ && (now - capture_start_) > 6000) {
    capturing_ = false;
    ESP_LOGI(TAG, "Message de demarrage du robot : %s", ver_buf_.c_str());
    size_t p = ver_buf_.find("release");
    if (p != std::string::npos) {
      size_t e = p;
      while (e < ver_buf_.size() && ver_buf_[e] != ' ' && ver_buf_[e] != '\n' && ver_buf_[e] != ':') e++;
      fw_version_ = ver_buf_.substr(p, e - p);
    } else {
      fw_version_ = "introuvable (voir les logs)";
    }
    ESP_LOGI(TAG, "Firmware du robot : %s", fw_version_.c_str());
    last_init_ms_ = now;
    init_();
  }

  // 2) robot endormi / flux perdu -> reveil periodique
  if (!capturing_ && !stream_ok() && (now - last_init_ms_) > 8000 && now > 3000) {
    ESP_LOGW(TAG, "Pas de flux OI, tentative de reveil (BRC + Start)");
    last_init_ms_ = now;
    wake();
  }

  // 3) maintien d'eveil : impulsion BRC toutes les 50 s si Passive et pas en train de nettoyer
  if (stream_ok() && !manual_ && mode_ == 1 && current_ma_ > -300 && (now - last_keepalive_ms_) > 50000) {
    last_keepalive_ms_ = now;
    pulse_brc_();
  }

  // 4) watchdog manette
  if (manual_) {
    if ((cmd_l_ != 0 || cmd_r_ != 0) && (now - last_drive_ms_) > 400) {
      ESP_LOGW(TAG, "Watchdog manette : arret");
      send_drive_(0, 0);
    }
    if ((now - last_drive_ms_) > 30000) {
      ESP_LOGI(TAG, "Fin de session manuelle -> Passive");
      manual_ = false;
      this->write_byte(128);
    }
    // le robot a quitte Safe tout seul (falaise, roue levee, chargeur...)
    if (mode_ == 1 && (now - manual_since_) > 800) {
      manual_ = false;
      cmd_l_ = cmd_r_ = 0;
    }
  }
}

void RoombaOI::read_version() {
  if (!stream_ok()) {
    ESP_LOGW(TAG, "Robot endormi : reveille-le d'abord (bouton CLEAN) puis relance");
    return;
  }
  manual_ = false;
  ver_buf_.clear();
  capturing_ = true;
  capture_start_ = millis();
  state_ = 0;
  this->write_byte(7);  // RESET : le robot redemarre et imprime sa version
}

void RoombaOI::feed_(uint8_t b) {
  if (capturing_) {
    if ((b >= 32 && b < 127) || b == '\n') {
      if (ver_buf_.size() < 1500) ver_buf_.push_back((char) b);
    }
    return;
  }
  switch (state_) {
    case 0:
      if (b == 19) state_ = 1;
      break;
    case 1:
      if (b == 0 || b > 60) {
        state_ = 0;
      } else {
        expect_ = b + 1;  // donnees + checksum
        pos_ = 0;
        state_ = 2;
      }
      break;
    case 2:
      buf_[pos_++] = b;
      if (pos_ >= expect_) {
        uint8_t n = expect_ - 1;
        uint8_t sum = 19 + n;
        for (uint8_t i = 0; i < expect_; i++) sum += buf_[i];
        if (sum == 0) {
          handle_frame_(buf_, n);
        }
        state_ = 0;
      }
      break;
  }
}

void RoombaOI::handle_frame_(const uint8_t *p, uint8_t len) {
  uint32_t now = millis();
  bool have_enc_l = false, have_enc_r = false;
  uint16_t el = 0, er = 0;
  uint8_t i = 0;
  while (i < len) {
    uint8_t id = p[i++];
    uint8_t l = pkt_len(id);
    if (i + l > len) break;
    uint16_t v16 = (l == 2) ? (uint16_t(p[i]) << 8 | p[i + 1]) : 0;
    uint8_t v8 = p[i];
    switch (id) {
      case 7:
        bumps_ = v8 & 0x03;
        wheeldrops_ = (v8 >> 2) & 0x03;
        break;
      case 9: cliffs_ = (cliffs_ & ~0x01) | (v8 ? 0x01 : 0); break;
      case 10: cliffs_ = (cliffs_ & ~0x02) | (v8 ? 0x02 : 0); break;
      case 11: cliffs_ = (cliffs_ & ~0x04) | (v8 ? 0x04 : 0); break;
      case 12: cliffs_ = (cliffs_ & ~0x08) | (v8 ? 0x08 : 0); break;
      case 21: charge_state_ = v8; break;
      case 22: voltage_mv_ = v16; break;
      case 23: current_ma_ = (int16_t) v16; break;
      case 24: temp_c_ = (int8_t) v8; break;
      case 25: charge_mah_ = v16; break;
      case 26: capacity_mah_ = v16; break;
      case 34: sources_ = v8; break;
      case 35: mode_ = v8; break;
      case 43: el = v16; have_enc_l = true; break;
      case 44: er = v16; have_enc_r = true; break;
      default: break;
    }
    i += l;
  }
  last_frame_ms_ = now;
  if (have_enc_l && have_enc_r) update_pose_(el, er, now);

  // front montant de pare-chocs -> instantane de pose
  uint8_t rising = bumps_ & ~last_bumps_;
  if (rising) {
    bump_count_++;
    bump_x_ = x_mm_;
    bump_y_ = y_mm_;
    bump_theta_ = theta_;
    bump_side_ = bumps_;  // bit0 droit, bit1 gauche
    // pare-chocs frontal complet contre un mur plat : recaler le cap sur 0/90/180/270
    if (wall_snap_ && bumps_ == 0x03 && !is_docked() && !manual_) {
      float nearest = std::round(theta_ / HALF_PI) * HALF_PI;
      float diff = wrap_pi(theta_ - nearest);
      if (std::fabs(diff) < 20.0f * DEG2RAD) {
        theta_ = wrap_pi(nearest);
        bump_theta_ = theta_;
        snap_count_++;
        ESP_LOGD(TAG, "Wall snap : correction %.1f deg", diff / DEG2RAD);
      }
    }
  }
  last_bumps_ = bumps_;

  // reset de pose quand le robot est pose sur la base et immobile
  if (is_docked()) {
    if (!dock_reset_done_ && still_frames_ > 130) {
      reset_pose();
      dock_reset_done_ = true;
      returning_ = false;
    }
  } else {
    dock_reset_done_ = false;
  }
}

void RoombaOI::set_gyro_z(float dps) {
  gyro_dps_ = dps;
  gyro_ms_ = millis();
}

void RoombaOI::update_pose_(uint16_t enc_l, uint16_t enc_r, uint32_t now) {
  if (!enc_init_) {
    enc_l_ = enc_l;
    enc_r_ = enc_r;
    last_pose_ms_ = now;
    enc_init_ = true;
    return;
  }
  int16_t dl = (int16_t)(enc_l - enc_l_);
  int16_t dr = (int16_t)(enc_r - enc_r_);
  enc_l_ = enc_l;
  enc_r_ = enc_r;
  float dt = (now - last_pose_ms_) / 1000.0f;
  last_pose_ms_ = now;
  if (dt <= 0 || dt > 0.5f) return;
  if (std::abs(dl) > 3000 || std::abs(dr) > 3000) return;  // glitch

  float sl = dl * MM_PER_COUNT * distance_scale_;
  float sr = dr * MM_PER_COUNT * distance_scale_;
  float ds = (sl + sr) * 0.5f;
  float dth_enc = (sr - sl) / wheel_base_mm_;

  if (dl == 0 && dr == 0) {
    if (still_frames_ < 100000) still_frames_++;
  } else {
    still_frames_ = 0;
  }

  float dth;
  bool gyro_valid = (now - gyro_ms_) < 200 && gyro_ms_ != 0;
  if (gyro_valid) {
    // biais : estime quand les roues sont immobiles depuis ~1 s
    if (still_frames_ > 60) gyro_bias_ += 0.01f * (gyro_dps_ - gyro_bias_);
    dth = (gyro_dps_ - gyro_bias_) * gyro_scale_ * DEG2RAD * dt;
    if (std::fabs(dth) < 0.0002f && still_frames_ > 0) dth = 0;  // bruit a l'arret
  } else {
    dth = dth_enc;
  }

  float mid = theta_ + dth * 0.5f;
  x_mm_ += ds * std::cos(mid);
  y_mm_ += ds * std::sin(mid);
  theta_ = wrap_pi(theta_ + dth);
  odo_total_mm_ += std::fabs(ds);
}

void RoombaOI::reset_pose() {
  x_mm_ = 0;
  y_mm_ = 0;
  theta_ = 0;
  ESP_LOGI(TAG, "Pose remise a zero (base)");
}

float RoombaOI::get_battery_pct() const {
  if (capacity_mah_ == 0) return 0;
  float p = 100.0f * charge_mah_ / capacity_mah_;
  return p > 100 ? 100 : p;
}

void RoombaOI::command_(uint8_t opcode) {
  uint32_t delay = 0;
  if (!stream_ok()) {
    pulse_brc_();
    this->set_timeout("cmd_init", 300, [this]() { this->init_(); });
    delay = 500;
  } else if (manual_) {
    send_drive_(0, 0);
    this->write_byte(128);
    manual_ = false;
    delay = 80;
  }
  returning_ = (opcode == 143);
  this->set_timeout("cmd_send", delay, [this, opcode]() { this->write_byte(opcode); });
}

void RoombaOI::stop() {
  // Safe prend la main sur n'importe quel cycle (nettoyage ou recherche de base), puis Passive
  returning_ = false;
  if (!stream_ok()) return;
  this->write_byte(131);
  this->set_timeout("stop_zero", 50, [this]() {
    this->send_drive_(0, 0);
    this->set_timeout("stop_passive", 100, [this]() {
      this->write_byte(128);
      this->manual_ = false;
    });
  });
}

void RoombaOI::locate() {
  // Play (141) n'est autorise qu'en Safe/Full (spec OI) : Safe, melodie, puis retour en Passive.
  if (!stream_ok() || manual_) return;
  this->write_byte(131);
  this->set_timeout("locate_song", 40, [this]() {
    const uint8_t song[] = {140, 0, 4, 72, 16, 79, 16, 72, 16, 79, 16};
    this->write_array(song, sizeof(song));
    this->set_timeout("locate_play", 30, [this]() {
      const uint8_t play[] = {141, 0};
      this->write_array(play, sizeof(play));
      this->set_timeout("locate_back", 1500, [this]() { this->write_byte(128); });
    });
  });
}

void RoombaOI::manual_mode(bool on) {
  if (on) {
    if (!stream_ok()) {
      wake();
      return;
    }
    if (!manual_) {
      this->write_byte(131);  // SAFE
      manual_ = true;
      returning_ = false;
      manual_since_ = millis();
    }
    last_drive_ms_ = millis();
  } else if (manual_) {
    send_drive_(0, 0);
    this->write_byte(128);
    manual_ = false;
  }
}

void RoombaOI::send_drive_(int l, int r) {
  cmd_l_ = l;
  cmd_r_ = r;
  int16_t rr = (int16_t) r, ll = (int16_t) l;
  uint8_t d[5] = {145, (uint8_t)((rr >> 8) & 0xFF), (uint8_t)(rr & 0xFF), (uint8_t)((ll >> 8) & 0xFF),
                  (uint8_t)(ll & 0xFF)};
  this->write_array(d, sizeof(d));
}

void RoombaOI::drive(int left, int right) {
  if (!manual_) manual_mode(true);
  if (!manual_) return;
  if (left > max_speed_) left = max_speed_;
  if (left < -max_speed_) left = -max_speed_;
  if (right > max_speed_) right = max_speed_;
  if (right < -max_speed_) right = -max_speed_;
  // en Safe, les pare-chocs ne coupent pas les moteurs : interdire d'avancer contre un obstacle
  if (bumps_ != 0 && left > 0 && right > 0) left = right = 0;
  last_drive_ms_ = millis();
  send_drive_(left, right);
}

void RoombaOI::drive_xy(float forward, float turn) {
  if (forward > 1) forward = 1;
  if (forward < -1) forward = -1;
  if (turn > 1) turn = 1;
  if (turn < -1) turn = -1;
  float l = forward - turn;
  float r = forward + turn;
  float m = std::max(1.0f, std::max(std::fabs(l), std::fabs(r)));
  drive((int) (l / m * max_speed_ * std::max(std::fabs(forward), std::fabs(turn))),
        (int) (r / m * max_speed_ * std::max(std::fabs(forward), std::fabs(turn))));
}

std::string RoombaOI::get_activity() const {
  if (!stream_ok()) return "asleep";
  if (manual_) return "manual";
  if (is_docked()) return is_charging() ? "charging" : "docked";
  if (mode_ == 1 && current_ma_ < -300) return returning_ ? "returning" : "cleaning";
  if ((sources_ & 0x01) != 0) return is_charging() ? "charging" : "docked";
  return "idle";
}

std::string RoombaOI::get_charge_text() const {
  switch (charge_state_) {
    case 0: return "not_charging";
    case 1: return "reconditioning";
    case 2: return "full_charging";
    case 3: return "trickle";
    case 4: return "waiting";
    case 5: return "fault";
    default: return "unknown";
  }
}

}  // namespace roomba_oi
}  // namespace esphome
