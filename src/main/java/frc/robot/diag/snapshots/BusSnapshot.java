package frc.robot.diag.snapshots;

// Plain data snapshot for roboRIO CAN controller health.
public final class BusSnapshot {
  public boolean valid = false;
  public double utilizationPct = 0.0;
  public int rxErrors = 0;
  public int txErrors = 0;
  public int rxDelta = 0;
  public int txDelta = 0;
  public int txFull = 0;
  public int txFullDelta = 0;
  public int busOff = 0;
  public int busOffDelta = 0;
  public double sampleAgeSec = 0.0;
}
