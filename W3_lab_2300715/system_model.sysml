package ThermalControlSystem {
    private import ScalarValues::*;

    part def BatteryPack {
        attribute capacityKwh : Real;
        attribute cellCount : Integer;
        attribute status : String = "ACTIVE";
    }
    part def ThermalSensor {
        attribute maxTempC : Real;
        attribute isCalibrated : Boolean;
        attribute status : String = "ACTIVE";
    }
    part def CoolingController {
        attribute targetTempC : Real;
        attribute status : String = "DRAFT";
    }
    requirement def MaxOperatingTempReq {
        attribute maxAllowedTempC : Real = 45.0;
        attribute status : String = "VERIFIED";
        require constraint { maxAllowedTempC <= 50.0 }
    }
}