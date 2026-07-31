/*******************************************************************************
* RobotKub TurtleBot3 Burger -- custom OpenCR firmware entry point (WRG2026).
*
* This sketch is intentionally the SAME thin wrapper as ROBOTIS's stock
* turtlebot3_burger example -- all the real firmware lives in the TurtleBot3_ROS2
* library (TurtleBot3Core). The customization we need is NOT here in the .ino;
* it is a ONE-LINE change inside that library that disables the push-button
* test-drive (see ../README.md and ../disable_test_drive.patch).
*
* Why: stock firmware hijacks SW1/SW2 to test-drive the robot (SW1 = forward
* 0.3 m, SW2 = spin 180 deg). We use those buttons for start/e-stop/resume from
* ROS instead, so the robot must NOT move on its own when a button is pressed.
* With the library patched, SW1/SW2 only report their state on /sensor_state,
* and ttb3_mission/button_handler decides what they mean.
*
* Based on ROBOTIS turtlebot3_burger.ino (Apache-2.0, Copyright 2016 ROBOTIS).
*******************************************************************************/

#include <TurtleBot3_ROS2.h>

/*******************************************************************************
* Setup function
*******************************************************************************/
void setup()
{
  // Begin TurtleBot3 core for support Burger.
  TurtleBot3Core::begin("Burger");
}

/*******************************************************************************
* Loop function
*******************************************************************************/
void loop()
{
  // Run TurtleBot3 core for communicating with ROS2 node, sensing several sensors and controlling actuators.
  TurtleBot3Core::run();
}
