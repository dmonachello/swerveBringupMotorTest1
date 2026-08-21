package frc.robot.manufacturers.ni.util;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import frc.robot.manufacturers.ni.diag.RoboRioPowerAttachment;
import frc.robot.manufacturers.ni.diag.RoboRioRailsAttachment;
import org.junit.jupiter.api.Test;

class RoboRioStatusReaderTest {
  private static final double INPUT_VOLTAGE = 12.4;
  private static final double BROWNOUT_VOLTAGE = 6.3;
  private static final double RAIL_3V3_VOLTAGE = 3.31;
  private static final double RAIL_3V3_CURRENT = 0.21;
  private static final int RAIL_3V3_FAULTS = 1;
  private static final double RAIL_5V_VOLTAGE = 5.02;
  private static final double RAIL_5V_CURRENT = 1.25;
  private static final int RAIL_5V_FAULTS = 2;
  private static final double RAIL_6V_VOLTAGE = 6.11;
  private static final double RAIL_6V_CURRENT = 2.5;
  private static final int RAIL_6V_FAULTS = 3;
  private static final double CAN_UTILIZATION_PCT = 37.5;
  private static final int CAN_RX_ERRORS = 4;
  private static final int CAN_TX_ERRORS = 5;
  private static final int CAN_BUS_OFF = 6;
  private static final int CAN_TX_FULL = 7;

  @Test
  void readerBuildsPowerAndRailAttachmentsFromTelemetrySource() {
    RoboRioStatusReader reader = new RoboRioStatusReader(new FakeTelemetrySource());

    RoboRioPowerAttachment power = reader.readPowerAttachment();
    RoboRioRailsAttachment rails = reader.readRailsAttachment();
    var bus = reader.readSharedBusAttachment();

    assertEquals(INPUT_VOLTAGE, power.inputVoltage);
    assertTrue(power.brownedOut);
    assertEquals(BROWNOUT_VOLTAGE, power.brownoutVoltage);
    assertEquals(RAIL_3V3_VOLTAGE, rails.rail3v3Voltage);
    assertEquals(RAIL_3V3_CURRENT, rails.rail3v3Current);
    assertTrue(rails.rail3v3Enabled);
    assertEquals(RAIL_3V3_FAULTS, rails.rail3v3FaultCount);
    assertEquals(RAIL_5V_VOLTAGE, rails.rail5vVoltage);
    assertEquals(RAIL_5V_CURRENT, rails.rail5vCurrent);
    assertFalse(rails.rail5vEnabled);
    assertEquals(RAIL_5V_FAULTS, rails.rail5vFaultCount);
    assertEquals(RAIL_6V_VOLTAGE, rails.rail6vVoltage);
    assertEquals(RAIL_6V_CURRENT, rails.rail6vCurrent);
    assertTrue(rails.rail6vEnabled);
    assertEquals(RAIL_6V_FAULTS, rails.rail6vFaultCount);
    assertEquals(CAN_UTILIZATION_PCT, bus.canUtilizationPct);
    assertEquals(CAN_RX_ERRORS, bus.canRxErrorCount);
    assertEquals(CAN_TX_ERRORS, bus.canTxErrorCount);
    assertEquals(CAN_BUS_OFF, bus.canBusOffCount);
    assertEquals(CAN_TX_FULL, bus.canTxFullCount);
  }

  private static final class FakeTelemetrySource implements RoboRioStatusReader.TelemetrySource {
    @Override
    public double inputVoltage() {
      return INPUT_VOLTAGE;
    }

    @Override
    public boolean brownedOut() {
      return true;
    }

    @Override
    public double brownoutVoltage() {
      return BROWNOUT_VOLTAGE;
    }

    @Override
    public double rail3v3Voltage() {
      return RAIL_3V3_VOLTAGE;
    }

    @Override
    public double rail3v3Current() {
      return RAIL_3V3_CURRENT;
    }

    @Override
    public boolean rail3v3Enabled() {
      return true;
    }

    @Override
    public int rail3v3FaultCount() {
      return RAIL_3V3_FAULTS;
    }

    @Override
    public double rail5vVoltage() {
      return RAIL_5V_VOLTAGE;
    }

    @Override
    public double rail5vCurrent() {
      return RAIL_5V_CURRENT;
    }

    @Override
    public boolean rail5vEnabled() {
      return false;
    }

    @Override
    public int rail5vFaultCount() {
      return RAIL_5V_FAULTS;
    }

    @Override
    public double rail6vVoltage() {
      return RAIL_6V_VOLTAGE;
    }

    @Override
    public double rail6vCurrent() {
      return RAIL_6V_CURRENT;
    }

    @Override
    public boolean rail6vEnabled() {
      return true;
    }

    @Override
    public int rail6vFaultCount() {
      return RAIL_6V_FAULTS;
    }

    @Override
    public double canUtilizationPct() {
      return CAN_UTILIZATION_PCT;
    }

    @Override
    public int canRxErrorCount() {
      return CAN_RX_ERRORS;
    }

    @Override
    public int canTxErrorCount() {
      return CAN_TX_ERRORS;
    }

    @Override
    public int canBusOffCount() {
      return CAN_BUS_OFF;
    }

    @Override
    public int canTxFullCount() {
      return CAN_TX_FULL;
    }
  }
}
