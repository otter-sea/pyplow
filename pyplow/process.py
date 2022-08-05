class Metadata(self):
    """
    A landsat metadata object. This class builds is attributes
    from the names of each tag in the xml formatted .MTL files that
    come with landsat data. So, any tag that appears in the MTL file
    will populate as an attribute of landsat_metadata.

    You can access explore these attributes by using, for example

    """

    def __init__(self, filename):
        """
        There are several critical attributes that keep a common
        naming convention between all landsat versions, so they are
        initialized in this class for good record keeping and reference
        """

        # custom attribute additions
        self.FILEPATH           = filename
        self.DATETIME_OBJ       = None

        # product metadata attributes
        self.LANDSAT_SCENE_ID   = None
        self.DATA_TYPE          = None
        self.ELEVATION_SOURCE   = None
        self.OUTPUT_FORMAT      = None
        self.SPACECRAFT_ID      = None
        self.SENSOR_ID          = None
        self.WRS_PATH           = None
        self.WRS_ROW            = None
        self.NADIR_OFFNADIR     = None
        self.TARGET_WRS_PATH    = None
        self.TARGET_WRS_ROW     = None
        self.DATE_ACQUIRED      = None
        self.SCENE_CENTER_TIME  = None

        # image attributes
        self.CLOUD_COVER        = None
        self.IMAGE_QUALITY_OLI  = None
        self.IMAGE_QUALITY_TIRS = None
        self.ROLL_ANGLE         = None
        self.SUN_AZIMUTH        = None
        self.SUN_ELEVATION      = None
        self.EARTH_SUN_DISTANCE = None    # calculated for Landsats before 8.

        # read the file and populate the MTL attributes
        self.grab_meta(self.FILEPATH)

    def grab_meta(self):
        """
        Parses the xml format landsat metadata "MTL.txt" file

        This function parses the xml format metadata file associated with landsat images.
        it outputs a class instance metadata object with all the attributes found in the MTL
        file for quick referencing by other landsat related functions.

        Custom additions to metadata:
            datetime_obj    a datetime object for the precise date and time of image
                            aquisition (in Z time!)

        Inputs:
        filename    the filepath to a landsat MTL file.

        Returns:
            meta        class object with all metadata attributes
        """
        # if the "filename" input is actually already a metadata class object, return it back.
        if inspect.isclass(self.FILEPATH):
            return (self.FILEPATH)

        fields = []
        values = []

        meta = landsat_metadata()

        with open(self.FILEPATH, 'r') as metadata:
            for line in metadata:
                # skips lines that contain "bad flags" denoting useless data AND lines
                # greater than 1000 characters. 1000 character limit works around an odd LC5
                # issue where the metadata has 40,000+ erroneous characters of whitespace
                bad_flags = ["END","GROUP"]
                if not any(x in line for x in bad_flags) and len(line)<=1000:
                    try:
                        line = line.replace("  ","")
                        line = line.replace("\n","")
                        field_name, field_value = line.split(' = ')
                        fields.append(field_name)
                        values.append(field_value)
                    except:
                        pass

        for i,f in enumerate(fields):
            #format fields without quotes,dates, or times in them as floats
            if not any(['"' in values[i], 'DATE' in fields[i], 'TIME' in fields[i]]):
                setattr(meta, fields[i], float(values[i]))
            else:
                values[i] = values[i].replace('"','')
                setattr(meta, fields[i], values[i])


        # only landsat 8 includes sun-earth-distance in MTL file, so calculate it for the others.
        # create datetime_obj attribute (drop decimal seconds)
        dto_string = self.DATE_ACQUIRED + self.SCENE_CENTER_TIME
        dto_string = dto_string.split(".")[0]
        self.DATETIME_OBJ = datetime.strptime(dto_string, "%Y-%m-%d%H:%M:%S")

        return meta
