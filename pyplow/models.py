import numpy as np
from datetime import datetime
import inspect

class Models(self):
    def __init__(self):
        self.metadata = metadata
        self.temperature_mean
        self.temperature_min
        self.temperature_max
        self.w = water
        self.red = red
        self.blue = blue
        self.green = green
        self.nir = nir
        self.swir1 = swir1
        self.swir2 = swir2


    def ndvi(self):
        """Normalized Difference Vegetation Index (NDVI)
        """
        ndvi = (self.nir - self.red)/(self.nir + self.red)
        return ndvi


    def evi(self):
        """Enhanced Vegetation Index (EVI)
        """
        evi = 2.5 * ((self.nir - self.red) /
                     (self.nir + (6 * self.red) - (7.5 * self.blue) + 1))
        return evi


    def lswi(self):
        """Land Surface Water Index (LSWI)
        """
        lswi = (self.nir - self.swir1) / (self.nir + self.swir1)
        return lswi


    def apar(self, linear_coef: float = 1.25):
        """Amount of PAR absorbed by chlorophyll in the crop canopy (APARchl)
        APARchl = FPARchl × PAR

        FPARchl is the fraction of PAR absorbed by chlorophyll in the canopy
        that is estimated as a linear function of EVI.

        Parameters
        ----------
        linear_coef : float
            linear_coeficient estimated from FPARchl and EVI.
        """
        fpar = linear_coef * (self.evi - 0.1)
        apar = fpar * self.par
        return apar


    def temperature(self, temp_opt: float = 25):
        """Effect of air temperature on Photosynthesis.

        Tmin, Topt, and Tmax are the minimum, optimal, and maximum air temperature
        of photosynthesis.

        Tscalar = (T − Tmin) × (T − Tmax)
                  ---------------------------------------
                  [(T − Tmin) × (T − Tmax)] − (T − Topt)²

        Parameters
        ----------
        temp_opt : float
            optimal temperatute, set as ~25⁰C for SE Brazil region.
        """
        temperature = ((self.temp_mean - self.temp_min)
                       * (self.temp_mean - self.temp_max))
                    / (((self.temp_mean - self.temp_min)
                        * (self.temp_mean - self.temp_max))
                        - (self.temp_mean - temp_opt)**2)
        return temperature


    def w(self):
        """Effect of water on photosynthesis (Wscalar)
        Estimated by the LSWI, and the maximum LSWI during the plant growing season
        is assumed to be the LSWImax.
        """
        w = 1 + self.lswi
            / 1 + max(self.lswi)
        return w


    def eg(self, e0: float = 0.075):
        """Light Use Efficiency (εg)
        (µmol CO2 µmol⁻¹ photosynthetic photon flux density (PPFD) or g C mol⁻¹ PPFD)

        εg = ε0 × Tscalar × Wscalar

        Tscalar and Wscalar scalars represent the effects of air temperature
        and water on the light use efficiency of vegetation, respectively.

        Parameters
        ----------
        e0 : float
            0.075 mol of CO2 mol⁻¹ PPFD (0.9 g C mol⁻¹ PPFD) as the parameter ε0
            for sugarcane (C4 plant).
        """
        eg = e0 * self.temperature * self.w
        return eg


    def vpm(self):
        """Vegetation Photosynthesis Model (VPM)
        estimates the daily Gross Primary Production (GPP) by multiplying the amount of
        PAR absorbed by chlorophyll in the crop canopy (APARchl) and the light use efficiency
        (Xiao et al. 2004; 2005).

        ---
        References
        Xiao, X.M.; Zhang, Q.Y.; Braswell, B.; Urbanski, S.; Boles, S.; Wofsy,
        S.; Berrien, M.; Ojima, D. Modeling gross primary production of temperate
        deciduous broadleaf forest using satellite images and climate data.
        Remote Sens. Environ. 2004, 91, 256–270.


        Xiao, X.M.; Zhang, Q.Y.; Hollinger, D.; Aber, J.; Moore, B. Modeling
        gross primary production of an evergreen needleleaf forest using modis
        and climate data. Ecol. Appl. 2005, 15, 954–969.
        """
        gpp = self.eg * self.apar
        return gpp
