
class MetadataHarmonisationError(Exception):
    """Metadata Harmonisation Error - used to catch transformation errors

    :param Exception: Raised when a harmonisation transformation fails.
    :type Exception: :class:`Exception`
    """    
    pass

class NotImplementedUnitConversionError(Exception):
    """Not Implemented Unit Conversion Error - used to catch unit conversion errors

    :param Exception: Raised when a unit conversion fails
    :type Exception: :class:`Exception`
    """
    pass

class NoUnitConversionError(Exception):
    """No Unit Conversion Error - used to catch unit conversion errors

    :param Exception: Raised when a unit conversion fails
    :type Exception: :class:`Exception`
    """
    pass

class ROICleanCheckFail(Exception):
    """ROI Clean Check Fails - used to detect ROI clean check errors

    :param Exception: Raised when an predicted value != the original value
    :type Exception: :class:`Exception`
    """
    pass

class ValidationError(Exception):
    """Import Validation Fails - used to detect import validation errors

    :param Exception: Raised when an expected value != the original value
    :type Exception: :class:`Exception`
    """
    pass

class UnharmonisedAnnotationException(Exception):
    """Import Validation Fails - used to detect import validation errors

    :param Exception: Raised when an expected value != the original value
    :type Exception: :class:`Exception`
    """
    pass

class PipelineTaskIDError(Exception):
    pass