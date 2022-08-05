import numpy as np
from datetime import datetime
import inspect

class Models(self):
    def __init__(self):
        self.metadata = metadata
        self.red = red
        self.blue = blue
        self.green = green
        self.nir = nir
        self.swir1 = swir1
        self.swir2 = swir2

    def ndvi(self):
        ndvi = (self.nir - self.red)/(self.nir + self.red)

        return ndvi

    def surface_temp(self,
                     k1:float,
                     k2:float,
                     rc:float,
                     lt6:float,
                     path_rad:float,
                     rsky:int,
                     enb:float = 10.2,
                     tnb:float = 11.3) -> float:
        """
        calculates the surface temperature with a modified plank equation
        following Markham and Barker.

                        K2
        Ts =    ----------------------
                ln((enb * K1 / Rc) +1)

        where
            K1  = constant 1, landsat specific
            K2  = constant 2, landsat specific
            Rc  = corrected thermal radiance
            enb = narrow band emissivity for thermal sensor wavelength band

        and

                    Lt6 - Rp (tnb)
            Rc =    --------------  - (1 - enb) * Rsky
                        tnb

        where
            Lt6 = spectral radience of landsat band 6
            path_rad  = path radiance in the (10.4 to 12.5 um) band
            Rsky= narrow band downward thermal radiation from clear sky
            tnb = narrow band transmissivity of air (10.4 to 12.5 um range)
        """

        correct_rad = ((lt6 - path_rad) / tnb) - ((1-enb) * rsky)
        surface_temp = (k2 / (np.ln(((enb * k1) / rc) + 1 )))

        return surface_temp
