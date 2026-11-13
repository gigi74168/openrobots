import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import uart
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]
CODEOWNERS = []

roomba_ns = cg.esphome_ns.namespace("roomba_oi")
RoombaOI = roomba_ns.class_("RoombaOI", cg.Component, uart.UARTDevice)

CONF_BRC_PIN = "brc_pin"
CONF_WALL_SNAP = "wall_snap"

# brc_pin : GPIO qui pilote la base d'un transistor NPN (BC547/2N2222) dont le
# collecteur va sur la broche 5 (BRC) du mini-DIN. GPIO a 1 = BRC tire a la masse.
CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(RoombaOI),
            cv.Required(CONF_BRC_PIN): pins.gpio_output_pin_schema,
            cv.Optional(CONF_WALL_SNAP, default=True): cv.boolean,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    pin = await cg.gpio_pin_expression(config[CONF_BRC_PIN])
    cg.add(var.set_brc_pin(pin))
    cg.add(var.set_wall_snap(config[CONF_WALL_SNAP]))
