
- Interesting bug trying to track down the `0.0` amps reading I am getting for a Spark MAX / NEO combo.
- I cross checked the data using the REV Hardware Client and graphed the amps.
- The REV Hardware Client showed a non-zero but spiky current reading.
- That means the motor current signal exists on the controller side, and the remaining bug is in how we are sampling or presenting it in bringup.
