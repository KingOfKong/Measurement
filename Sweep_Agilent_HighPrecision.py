# -*- coding: latin-1 -*-
import math, time
from pymeasure.units.unit import NANOMETER, PICOMETER, MILLISECOND, DBM, SECOND, MILLIWATT
from pymeasure.instruments.exceptions import InstrumentError, InstrumentRuntimeError, InstrumentValueError
from pymeasure.instruments.Agilent.tunable_laser import Agilent8164AB
import pylab
import numpy as np


class AGILENT_SWEEP(object):

    def __init__(self):        
        self.mainframe = Agilent8164AB( name = "AGILENT 8164AB Lightwave Measurement System", address = "GPIB::25" )        
        self.mainframe.timeout = 60 * SECOND
        self.laser = self.mainframe.TL81980A( slot = 1 )
        self.sensor = self.mainframe.PM81635A( slot = 2 )
        #self.sensor.range = 0 * DBM
        #self.laser.wavelength = 1550 * NANOMETER
        self.laser.power = 6 * DBM
        # flush old results
        self.sensor.get_function_result()
        self.laser.get_lambda_logging()
                    
    def continuous_sweep(self,
                         start_wavelength=1465*NANOMETER,
                         scan_range=100*NANOMETER,
                         resolution_wavelength=1*PICOMETER,
                         averaging_time=0.5*MILLISECOND,
                         laser_power=None,
                         preprint = '    +', 
                         sensor_range= -30*DBM):

        mainframe, laser, sensor = self.mainframe, self.laser, self.sensor
        begin_wl = laser.wavelength
               
        print preprint, "+++++++++++++++++++++++ begin laser sweep +++++++++++++++++++++++"
        stop_wavelength = start_wavelength + scan_range
        _sweep_speed = resolution_wavelength.get_value(NANOMETER) / averaging_time.get_value(SECOND)
        _sweep_speed = round(_sweep_speed, 3)        
        for x in laser.sweep_speed_allowed_values:
            if x.get_value(NANOMETER) <= _sweep_speed:
                sweep_speed = x
        
        number_data_points = int(math.floor( (scan_range-resolution_wavelength)/resolution_wavelength)) + 1
        
        print preprint, "sweep from %s to %s"%(start_wavelength, start_wavelength + scan_range)
        print preprint, "resolution wavelength:", resolution_wavelength    
        print preprint, "number of data points:", number_data_points
#        print preprint, "sweep_speed will be set to: %f nm/s"%sweep_speed.get_value(PICOMETER)
                
        if number_data_points > sensor.__nbr_datapoints_max__:
            message = "number of data points (%d) should be <= %d"%(number_data_points,sensor.__nbr_datapoints_max__)
            raise InstrumentValueError(message)
            
        # ####################################
        #
        #  Set sweep parameters
        # 
        laser.sweep_mode = 'CONT' 
        laser.sweep_speed = sweep_speed
        laser.sweep_start = start_wavelength
        laser.sweep_stop = stop_wavelength - resolution_wavelength
        laser.sweep_step = resolution_wavelength 
        laser.sweep_cycles = 1
        ''' Lambda logging is a feature that records the exact wavelength
            of a tunable laser module when a trigger is generated during a continuous sweep. You
            can read this data using the [:SOURce[n]][:CHANnel[m]]:READout:DATA? command.
        '''
        laser.sweep_lambda_logging = True    
        
        # ####################################
        #
        #  Set trigger behavior
        #
        ''' Generate output trigger every time a sweep step finishes. '''
        laser.trigger_input = 'IGNORE'
        laser.trigger_output = 'STFINISHED'
        ''' SMEasure: Start a single measurement. If a measurement function is active, see “:SENSe[n][:CHANnel[m]]:FUNCtion:STATe” on page 92, 
            one sample is performed and the result is stored in the data array '''
        sensor.trigger_input = 'SMEASURE'
        sensor.triger_output = 'DISABLED'
        ''' The same as DEFault but a trigger at the Output Trigger Connector generates a trigger at the Input Trigger Connector automatically.'''
        mainframe.trigger_configuration = 'LOOPBACK'
        
        # laser has built in procedure to check if the sweep parameters are valid and consistent
        result = laser.sweep_check_params()
        print preprint, "sweep_check_params() returns: %r"%result
        if not result == '0,OK':
            raise RuntimeError

        
        sensor.range_auto = False
        sensor.range = sensor_range
        sensor.logging_parameters = number_data_points, averaging_time    
        if laser_power:
            laser.power = laser_power
            print preprint, "laser power set to", laser.power
        sensor.function_start('LOGGING')
        laser.sweep_state = 'START'
        
        print preprint, "sweeping",  
        while 1:
            laser_sweep_state = laser.sweep_state
            #sensor_function_state = sensor.get_function_state()
            #print "laser, sensor = ",(laser_sweep_state, sensor_function_state)
            print ". ",
            if laser.sweep_state == 0:
                break
            time.sleep(.25)
        print
        
        time.sleep(1)
        
        
        powers = sensor.get_function_result()
        sensor.function_stop('LOGGING')
        wavelengths = laser.get_lambda_logging()
        #print sensor_results, len(sensor_results)
        #print wavelengths, len(wavelengths)
        laser.sweep_state = 'STOP'
        s = (len(wavelengths),len(powers))
        message = "got %d wavelenghts and %d powers"%s
        print preprint, message        
        m, M = min(s), max(s)
        if m != M:
            if M-m > 1:            
                raise InstrumentError(message)
            wavelengths = wavelengths[:m]
            powers = powers[:m]
        print preprint, "+++++++++++++++++++++++ end laser sweep +++++++++++++++++++++++\n"
        
        sensor.trigger_input = 'IGNORE'
        laser.wavelength = begin_wl
        return wavelengths * 1e9, powers
   
        
def agilent_sweep(): 
    filename = "2.fuckthisshit_phc.txt"
    #file = "test"
    #filename_gen = "TL-APCPC-PC-PM_FullSweep"
    outfile = open(filename,'w') 
    
    A = AGILENT_SWEEP()
    start_wl= 1465
    end_wl= 1575
    sensor_rng=-70
    resolution_wl=0.005
    current_startwl=start_wl
    wavelengths=[]
    powers=[]
    lim_datapoint=20000
    while current_startwl < end_wl:
        scan_rng= min(lim_datapoint*resolution_wl, end_wl-current_startwl)
        wavelengths_tmp, powers_tmp = A.continuous_sweep( start_wavelength = current_startwl * NANOMETER, 
                                                  scan_range = scan_rng * NANOMETER, 
                                                  resolution_wavelength=resolution_wl * NANOMETER, 
                                                  averaging_time = 1*MILLISECOND, 
                                                  sensor_range= sensor_rng*DBM ) 
        
        current_startwl=current_startwl+lim_datapoint*resolution_wl
        wavelengths=np.concatenate((wavelengths,wavelengths_tmp),axis=0)
        powers=np.concatenate((powers,powers_tmp),axis=0)
    pylab.plot( wavelengths, powers )
    pylab.grid()
    pylab.savefig("%s.png"%(filename))
    pylab.show()
    #pylab.savefig()
    data_values = [wavelengths, powers]
    data_values = np.transpose(data_values)
    for values in data_values:
        
        print >> outfile, values[0], values[1]
        outfile.flush()
    outfile.close()
    
    outfile = open(filename + '_exif.txt','w')
    print >> outfile, start_wl, end_wl, sensor_rng, resolution_wl
    outfile.close()
if __name__ == '__main__':
    agilent_sweep()
    

    

