package frc.robot.manufacturers;

import frc.robot.BringupUtil;
import frc.robot.devices.DeviceUnit;

@FunctionalInterface
public interface DeviceFactory {
  DeviceUnit create(BringupUtil.DeviceConfig config);
}
