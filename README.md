# TmaxMicro
This is some additional hardware an software to accomplish the following in the M3D Micro 3D Printer:

  * Add a temperature controled heated bed for ABS and PLA prints. The heated bed was done using a 2mm aluminium plate and 24 5W resistorts to heat it. Above the aluminium plate there is a 2mm glass.
  * Add a graphics LCD to show the print progress, elapsed and estimated time to finish as well as extruder and bed temperature and some other parameters.
  * Allows to use the printer withouth a PC, I only have my laptop and I move it a lot so it was a big deal to me. This also reduces power consumption, I'm using a Pandaboard I had lying around that consumes 10W at most.
  * Allows me to control the printer through internet or my network using Octoprint and [M3D-Fio](https://github.com/donovan6000/M3D-Fio) developed by [donovan6000](https://github.com/donovan6000) that did an amazing job.
  
The Pandaboard controls the printer through the USB connection and communicates throught the UART port to a PIC24 microcontroller that controls the graphical LCD and the bed temperature. Everything is powered from an ATX power supply, this allows me for example to automatically shutdown everything when a print is finished.
  
