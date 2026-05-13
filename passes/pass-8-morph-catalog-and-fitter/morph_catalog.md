# CharMorph mb_female morph catalog

Total sliders: **216**

Generated from `external/CharMorph-db/characters/mb_female/morphs/L2_packed/{__main__,Caucasian}.npz`.


## How to use

Each slider name maps to one or more storage entries (`*_max`, `*_min`, or combo corners `*_max-max` etc.). 
Set values in `configs/<body>.json::charmorph.morph_values` using the slider names below. 
Range is [0, 1] for `_max` direction; [-1, 0] uses the corresponding `_min` morph.


When two sliders are listed as 'compound with' each other, they're stored as a 2D combo grid; you can set them independently and the combo math handles the interaction.


## Body-measurement-relevant regions (use these for fitting)


### abdomen

- **Abdomen_Mass** — combo-paired with: Abdomen_Tone
- **Abdomen_Tone** — combo-paired with: Abdomen_Mass

### arms

- **Armpit_PosZ** — 1D slider
- **Arms_ForearmLength** — 1D slider
- **Arms_ForearmMass** — combo-paired with: Arms_ForearmTone
- **Arms_ForearmSize** — 1D slider
- **Arms_ForearmTone** — combo-paired with: Arms_ForearmMass
- **Arms_UpperarmGirth** — 1D slider
- **Arms_UpperarmLength** — 1D slider
- **Arms_UpperarmMass** — combo-paired with: Arms_UpperarmTone
- **Arms_UpperarmSize** — 1D slider
- **Arms_UpperarmTone** — combo-paired with: Arms_UpperarmMass
- **Elbows_Size** — 1D slider
- **Wrists_Size** — 1D slider

### body global

- **Body_Size** — 1D slider

### feet

- **Feet_HeelWidth** — 1D slider
- **Feet_Mass** — 1D slider
- **Feet_Size** — 1D slider
- **Feet_SizeX** — 1D slider
- **Feet_SizeY** — 1D slider
- **Feet_SizeZ** — 1D slider

### hands

- **Hands_FingersDiam** — 1D slider
- **Hands_FingersInterDist** — 1D slider
- **Hands_FingersLength** — 1D slider
- **Hands_FingersTipSize** — 1D slider
- **Hands_Length** — 1D slider
- **Hands_Mass** — combo-paired with: Hands_Tone
- **Hands_NailsLength** — 1D slider
- **Hands_PalmLength** — 1D slider
- **Hands_Size** — 1D slider
- **Hands_Tone** — combo-paired with: Hands_Mass

### head

- **Head_CraniumDolichocephalic** — 1D slider
- **Head_CraniumPentagonoides** — 1D slider
- **Head_CraniumPlatycephalus** — 1D slider
- **Head_Flat** — 1D slider
- **Head_Nucha** — 1D slider
- **Head_Size** — 1D slider
- **Head_SizeX** — 1D slider
- **Head_SizeY** — 1D slider
- **Head_SizeZ** — 1D slider

### legs

- **Legs_AnkleSize** — 1D slider
- **Legs_Bow** — 1D slider
- **Legs_CalfGirth** — 1D slider
- **Legs_KneeProminence** — 1D slider
- **Legs_KneeSize** — 1D slider
- **Legs_LowerThighGirth** — 1D slider
- **Legs_LowerlegLength** — 1D slider
- **Legs_LowerlegSize** — 1D slider
- **Legs_LowerlegsMass** — combo-paired with: Legs_LowerlegsTone
- **Legs_LowerlegsTone** — combo-paired with: Legs_LowerlegsMass
- **Legs_UpperThighGirth** — 1D slider
- **Legs_UpperlegInCurve** — 1D slider
- **Legs_UpperlegLength** — 1D slider
- **Legs_UpperlegSize** — 1D slider
- **Legs_UpperlegsMass** — combo-paired with: Legs_UpperlegsTone
- **Legs_UpperlegsTone** — combo-paired with: Legs_UpperlegsMass

### neck

- **Neck_Angle** — 1D slider
- **Neck_Back** — 1D slider
- **Neck_Collarbone** — 1D slider
- **Neck_Length** — 1D slider
- **Neck_Mass** — combo-paired with: Neck_Tone
- **Neck_SideCurve** — 1D slider
- **Neck_Size** — 1D slider
- **Neck_Tone** — combo-paired with: Neck_Mass
- **Neck_TrapeziousSize** — 1D slider

### pelvis

- **Pelvis_Angle** — 1D slider
- **Pelvis_CrotchDist** — 1D slider
- **Pelvis_CrotchVolume** — 1D slider
- **Pelvis_Girth** — 1D slider
- **Pelvis_GluteusMass** — combo-paired with: Pelvis_GluteusTone
- **Pelvis_GluteusSize** — 1D slider
- **Pelvis_GluteusTone** — combo-paired with: Pelvis_GluteusMass
- **Pelvis_Length** — 1D slider
- **Pelvis_SizeX** — 1D slider
- **Pelvis_SizeY** — 1D slider

### shoulders

- **Shoulders_Length** — 1D slider
- **Shoulders_Mass** — combo-paired with: Shoulders_Tone
- **Shoulders_PosZ** — 1D slider
- **Shoulders_Size** — 1D slider
- **Shoulders_SizeX** — 1D slider
- **Shoulders_SizeX2** — 1D slider
- **Shoulders_Tone** — combo-paired with: Shoulders_Mass

### stomach

- **Stomach_LocalFat** — 1D slider
- **Stomach_Volume** — 1D slider

### torso

- **Torso_AureolaSize** — combo-paired with: Torso_BreastMass
- **Torso_BellyPosZ** — 1D slider
- **Torso_Dorsi** — 1D slider
- **Torso_Length** — 1D slider
- **Torso_Mass** — combo-paired with: Torso_BreastMass, Torso_BreastTone, Torso_Tone
- **Torso_SizeX** — 1D slider
- **Torso_SizeY** — 1D slider
- **Torso_Tone** — combo-paired with: Torso_BreastMass, Torso_BreastTone, Torso_Mass
- **Torso_ToracicCurve** — 1D slider
- **Torso_Vshape** — 1D slider

### torso/breast

- **Torso_BreastMass** — combo-paired with: Torso_AureolaSize, Torso_BreastPosX, Torso_BreastScaleY, Torso_BreastTone, Torso_Mass, Torso_Tone
- **Torso_BreastNipple** — 1D slider
- **Torso_BreastPosX** — combo-paired with: Torso_BreastMass
- **Torso_BreastPosZ** — 1D slider
- **Torso_BreastScaleY** — combo-paired with: Torso_BreastMass
- **Torso_BreastTone** — combo-paired with: Torso_BreastMass, Torso_Mass, Torso_Tone

### waist

- **Waist_Size** — 1D slider


## Face / cosmetic regions (not used by the fitter)


### face/cheeks

- Cheeks_CreaseExt
- Cheeks_InfraVolume
- Cheeks_Mass
- Cheeks_SideCrease
- Cheeks_Tone
- Cheeks_Zygom
- Cheeks_ZygomPosZ

### face/chin

- Chin_Cleft
- Chin_Prominence
- Chin_SizeX
- Chin_SizeZ
- Chin_Tone
- Jaw_Angle
- Jaw_Angle2
- Jaw_LocY
- Jaw_Prominence
- Jaw_ScaleX

### face/ears

- Ears_Lobe
- Ears_LocY
- Ears_LocZ
- Ears_RotX
- Ears_Round
- Ears_SizeX
- Ears_SizeY
- Ears_SizeZ

### face/eyes

- Eyes_BagProminence
- Eyes_BagSize
- Eyes_Crosscalibration
- Eyes_InnerPosX
- Eyes_InnerPosZ
- Eyes_IrisSize
- Eyes_OuterPosX
- Eyes_OuterPosZ
- Eyes_PosX
- Eyes_PosZ
- Eyes_Size
- Eyes_SizeZ
- Eyes_TypeAlmond
- Eyes_TypeHooded
- Eyes_innerSinus

### face/forehead

- Forehead_Angle
- Forehead_Curve
- Forehead_SizeX
- Forehead_SizeZ
- Forehead_Temple

### face/mouth

- Mouth_CornersPosZ
- Mouth_LowerlipExt
- Mouth_LowerlipSizeZ
- Mouth_LowerlipVolume
- Mouth_PhiltrumProminence
- Mouth_PhiltrumSizeX
- Mouth_PhiltrumSizeY
- Mouth_PosY
- Mouth_PosZ
- Mouth_Protusion
- Mouth_SideCrease
- Mouth_SizeX
- Mouth_UpperlipExt
- Mouth_UpperlipSizeZ
- Mouth_UpperlipVolume

### face/nose

- Nose_BallSizeX
- Nose_BasePosZ
- Nose_BaseShape
- Nose_BaseSizeX
- Nose_BaseSizeZ
- Nose_BridgeSizeX
- Nose_Curve
- Nose_GlabellaPosZ
- Nose_GlabellaSizeX
- Nose_GlabellaSizeY
- Nose_NostrilCrease
- Nose_NostrilDiam
- Nose_NostrilPosZ
- Nose_NostrilSizeX
- Nose_NostrilSizeY
- Nose_NostrilSizeZ
- Nose_PosY
- Nose_SeptumFlat
- Nose_SeptumRolled
- Nose_SizeY
- … and 7 more

### face/other

- Face_Ellipsoid
- Face_Parallelepiped
- Face_Triangle

### other

- Chest_Girth
- Chest_SizeX
- Chest_SizeY
- Chest_SizeZ
- Eyebrows_Angle
- Eyebrows_Droop
- Eyebrows_PosZ
- Eyebrows_Ridge
- Eyebrows_SizeY
- Eyebrows_Tone
- Eyelids_Angle
- Eyelids_Crease
- Eyelids_InnerPosZ
- Eyelids_LowerCurve
- Eyelids_MiddlePosZ
- Eyelids_OuterPosZ
- Eyelids_SizeZ
- Fantasy_EarsNone
- Fantasy_EarsPointRotation
- Fantasy_EarsPointed
- … and 5 more