# CharMorph morph sensitivity catalog

For every slider, the cm change in each body measurement when the slider goes from 0 → 1 (evaluated at the default mesh, all other morphs at 0).


Use this as a manual lookup table. Example: to make the waist 5 cm smaller, look up the slider whose `waist_cm` is the most negative; if it's -3.0 cm/unit, push it to ~1.67 (out of 1.0 = clamp).


## Baseline (default-mesh measurements, cm)

- **stature_cm**: 167.99
- **shoulder_breadth_cm**: 36.69
- **hip_width_cm**: 38.24
- **bust_cm**: 84.69
- **waist_cm**: 52.90
- **hip_cm**: 95.42
- **thigh_circ_cm**: 48.02
- **knee_circ_cm**: 36.97
- **calf_circ_cm**: 33.97
- **upper_arm_circ_cm**: 47.69
- **forearm_circ_cm**: 69.33

## Top 10 influencers per measurement


### `stature_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Pelvis_Length** | +5.89 | pelvis |
| **Torso_Length** | +5.43 | torso |
| **Chest_SizeZ** | +3.51 | other |
| **Neck_Length** | +3.44 | neck |
| **Head_SizeZ** | +3.02 | head |
| **Forehead_SizeZ** | +2.76 | face/forehead |
| **Head_Size** | +2.72 | head |
| **Face_Triangle** | +1.10 | face/other |
| **Head_CraniumPlatycephalus** | -0.96 | head |
| **Face_Parallelepiped** | -0.41 | face/other |

### `shoulder_breadth_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Shoulders_SizeX** | +5.38 | shoulders |
| **Torso_Vshape** | +4.72 | torso |
| **Torso_SizeX** | +3.40 | torso |
| **Shoulders_SizeX2** | +2.98 | shoulders |
| **Shoulders_Length** | +2.74 | shoulders |
| **Shoulders_Mass** | +1.85 | shoulders |
| **Shoulders_Tone** | +1.45 | shoulders |
| **Shoulders_Size** | +0.86 | shoulders |
| **Arms_UpperarmGirth** | +0.64 | arms |
| **Torso_Mass** | +0.21 | torso |

### `hip_width_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Pelvis_GluteusSize** | +8.16 | pelvis |
| **Legs_UpperlegsMass** | +6.34 | legs |
| **Pelvis_SizeX** | +3.06 | pelvis |
| **Legs_UpperThighGirth** | +3.02 | legs |
| **Legs_UpperlegSize** | +2.70 | legs |
| **Legs_Bow** | +2.28 | legs |
| **Pelvis_GluteusMass** | +2.17 | pelvis |
| **Pelvis_Girth** | +1.64 | pelvis |
| **Legs_UpperlegsTone** | +0.76 | legs |
| **Torso_Mass** | +0.46 | torso |

### `bust_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Torso_Mass** | +23.05 | torso |
| **Torso_Tone** | +10.46 | torso |
| **Torso_Vshape** | +9.37 | torso |
| **Chest_Girth** | +7.40 | other |
| **Torso_SizeY** | +7.25 | torso |
| **Torso_SizeX** | +6.64 | torso |
| **Chest_SizeY** | +6.35 | other |
| **Torso_Dorsi** | +6.08 | torso |
| **Torso_BreastScaleY** | +4.09 | torso/breast |
| **Shoulders_Mass** | +3.21 | shoulders |

### `waist_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Torso_Mass** | +26.93 | torso |
| **Stomach_LocalFat** | +18.39 | stomach |
| **Waist_Size** | +8.39 | waist |
| **Torso_SizeX** | +6.53 | torso |
| **Stomach_Volume** | +6.18 | stomach |
| **Torso_Vshape** | +3.08 | torso |
| **Pelvis_Angle** | +1.89 | pelvis |
| **Torso_SizeY** | +1.10 | torso |
| **Abdomen_Tone** | +0.88 | abdomen |
| **Pelvis_GluteusSize** | +0.86 | pelvis |

### `hip_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Pelvis_GluteusSize** | +17.60 | pelvis |
| **Legs_UpperlegsMass** | +15.43 | legs |
| **Pelvis_GluteusMass** | +14.70 | pelvis |
| **Legs_UpperlegSize** | +8.51 | legs |
| **Legs_UpperThighGirth** | +8.18 | legs |
| **Pelvis_SizeX** | +6.12 | pelvis |
| **Torso_Mass** | +5.59 | torso |
| **Pelvis_Girth** | +4.04 | pelvis |
| **Legs_Bow** | +3.87 | legs |
| **Pelvis_SizeY** | +2.17 | pelvis |

### `thigh_circ_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Legs_UpperlegsMass** | +17.34 | legs |
| **Legs_UpperlegSize** | +11.55 | legs |
| **Legs_LowerThighGirth** | +7.89 | legs |
| **Legs_UpperlegsTone** | +5.58 | legs |
| **Legs_Bow** | +2.76 | legs |
| **Legs_UpperlegInCurve** | -1.75 | legs |
| **Pelvis_GluteusSize** | +0.67 | pelvis |
| **Legs_KneeProminence** | +0.44 | legs |
| **Pelvis_GluteusMass** | +0.08 | pelvis |
| **Torso_Mass** | +0.06 | torso |

### `knee_circ_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Legs_LowerlegsMass** | +4.82 | legs |
| **Legs_CalfGirth** | +4.79 | legs |
| **Legs_LowerlegSize** | +4.12 | legs |
| **Legs_LowerlegsTone** | +1.16 | legs |
| **Legs_KneeSize** | +1.05 | legs |
| **Legs_UpperlegSize** | +1.01 | legs |
| **Legs_UpperlegsMass** | +0.97 | legs |
| **Legs_KneeProminence** | +0.77 | legs |
| **Legs_UpperlegsTone** | -0.28 | legs |

### `calf_circ_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Legs_LowerlegsMass** | +9.14 | legs |
| **Legs_LowerlegSize** | +6.04 | legs |
| **Legs_CalfGirth** | +5.18 | legs |
| **Legs_LowerlegsTone** | +2.21 | legs |
| **Legs_AnkleSize** | +0.70 | legs |
| **Legs_Bow** | +0.09 | legs |

### `upper_arm_circ_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Shoulders_Mass** | +5.48 | shoulders |
| **Torso_SizeY** | +5.04 | torso |
| **Shoulders_SizeX** | +4.94 | shoulders |
| **Torso_Vshape** | +4.32 | torso |
| **Shoulders_Tone** | +3.85 | shoulders |
| **Torso_Mass** | +2.81 | torso |
| **Shoulders_Length** | +2.78 | shoulders |
| **Shoulders_SizeX2** | +2.64 | shoulders |
| **Neck_Mass** | +1.95 | neck |
| **Shoulders_Size** | +1.86 | shoulders |

### `forearm_circ_cm`
| slider | Δ cm | region |
| --- | --- | --- |
| **Torso_Mass** | +8.01 | torso |
| **Torso_SizeY** | +5.99 | torso |
| **Arms_UpperarmLength** | +5.54 | arms |
| **Shoulders_SizeX** | +4.96 | shoulders |
| **Arms_UpperarmMass** | +3.75 | arms |
| **Arms_UpperarmGirth** | +3.68 | arms |
| **Torso_Tone** | +3.56 | torso |
| **Shoulders_Length** | +3.53 | shoulders |
| **Chest_SizeY** | +3.42 | other |
| **Arms_UpperarmSize** | +3.10 | arms |

## Full table grouped by region


### abdomen

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Abdomen_Mass` | · | · | · | · | +0.85 | · | · | · | · | · | · |
| `Abdomen_Tone` | · | · | · | · | +0.88 | · | · | · | · | · | · |

### arms

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Armpit_PosZ` | · | · | · | +0.36 | · | · | · | · | · | · | -0.22 |
| `Arms_ForearmLength` | · | · | · | · | · | · | · | · | · | · | · |
| `Arms_ForearmMass` | · | · | · | · | · | · | · | · | · | · | · |
| `Arms_ForearmSize` | · | · | · | · | · | · | · | · | · | · | · |
| `Arms_ForearmTone` | · | · | · | · | · | · | · | · | · | · | · |
| `Arms_UpperarmGirth` | · | +0.64 | · | +0.99 | · | · | · | · | · | +1.38 | +3.68 |
| `Arms_UpperarmLength` | · | · | · | · | · | · | · | · | · | · | +5.54 |
| `Arms_UpperarmMass` | · | · | · | · | · | · | · | · | · | · | +3.75 |
| `Arms_UpperarmSize` | · | · | · | · | · | · | · | · | · | · | +3.10 |
| `Arms_UpperarmTone` | · | · | · | · | · | · | · | · | · | · | +2.05 |
| `Elbows_Size` | · | · | · | · | · | · | · | · | · | · | · |
| `Wrists_Size` | · | · | · | · | · | · | · | · | · | · | · |

### face/forehead

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Forehead_Angle` | · | · | · | · | · | · | · | · | · | · | · |
| `Forehead_Curve` | · | · | · | · | · | · | · | · | · | · | · |
| `Forehead_SizeX` | · | · | · | · | · | · | · | · | · | · | · |
| `Forehead_SizeZ` | +2.76 | · | · | · | · | · | · | · | · | · | · |
| `Forehead_Temple` | · | · | · | · | · | · | · | · | · | · | · |

### face/other

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Face_Ellipsoid` | · | · | · | · | · | · | · | · | · | · | · |
| `Face_Parallelepiped` | -0.41 | · | · | · | · | · | · | · | · | · | · |
| `Face_Triangle` | +1.10 | · | · | · | · | · | · | · | · | · | · |

### feet

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Feet_HeelWidth` | · | · | · | · | · | · | · | · | · | · | · |
| `Feet_Mass` | · | · | · | · | · | · | · | · | · | · | · |
| `Feet_Size` | · | · | · | · | · | · | · | · | · | · | · |
| `Feet_SizeX` | · | · | · | · | · | · | · | · | · | · | · |
| `Feet_SizeY` | · | · | · | · | · | · | · | · | · | · | · |
| `Feet_SizeZ` | +0.30 | · | · | · | · | · | · | · | · | · | · |

### head

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Head_CraniumDolichocephalic` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_CraniumPentagonoides` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_CraniumPlatycephalus` | -0.96 | · | · | · | · | · | · | · | · | · | · |
| `Head_Flat` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_Nucha` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_Size` | +2.72 | · | · | · | · | · | · | · | · | -0.37 | · |
| `Head_SizeX` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_SizeY` | · | · | · | · | · | · | · | · | · | · | · |
| `Head_SizeZ` | +3.02 | · | · | · | · | · | · | · | · | · | · |

### legs

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Legs_AnkleSize` | · | · | · | · | · | · | · | · | +0.70 | · | · |
| `Legs_Bow` | · | · | +2.28 | · | · | +3.87 | +2.76 | · | +0.09 | · | · |
| `Legs_CalfGirth` | · | · | · | · | · | · | · | +4.79 | +5.18 | · | · |
| `Legs_KneeProminence` | · | · | · | · | · | · | +0.44 | +0.77 | · | · | · |
| `Legs_KneeSize` | · | · | · | · | · | · | · | +1.05 | · | · | · |
| `Legs_LowerThighGirth` | · | · | · | · | · | · | +7.89 | · | · | · | · |
| `Legs_LowerlegLength` | · | · | · | · | · | · | · | · | · | · | · |
| `Legs_LowerlegSize` | · | · | · | · | · | · | · | +4.12 | +6.04 | · | · |
| `Legs_LowerlegsMass` | · | · | · | · | · | · | · | +4.82 | +9.14 | · | · |
| `Legs_LowerlegsTone` | · | · | · | · | · | · | · | +1.16 | +2.21 | · | · |
| `Legs_UpperThighGirth` | · | · | +3.02 | · | · | +8.18 | +0.05 | · | · | · | · |
| `Legs_UpperlegInCurve` | · | · | · | · | · | · | -1.75 | · | · | · | · |
| `Legs_UpperlegLength` | · | · | · | · | · | · | · | · | · | · | · |
| `Legs_UpperlegSize` | · | · | +2.70 | · | · | +8.51 | +11.55 | +1.01 | · | · | · |
| `Legs_UpperlegsMass` | · | · | +6.34 | · | · | +15.43 | +17.34 | +0.97 | · | · | · |
| `Legs_UpperlegsTone` | · | · | +0.76 | · | · | +1.87 | +5.58 | -0.28 | · | · | · |

### neck

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Neck_Angle` | · | · | · | · | · | · | · | · | · | -0.15 | · |
| `Neck_Back` | · | · | · | · | · | · | · | · | · | · | · |
| `Neck_Collarbone` | · | · | · | · | · | · | · | · | · | +0.24 | · |
| `Neck_Length` | +3.44 | · | · | · | · | · | · | · | · | · | · |
| `Neck_Mass` | · | · | · | · | · | · | · | · | · | +1.95 | +0.18 |
| `Neck_SideCurve` | · | · | · | · | · | · | · | · | · | -0.09 | · |
| `Neck_Size` | · | · | · | · | · | · | · | · | · | -0.19 | · |
| `Neck_Tone` | · | · | · | · | · | · | · | · | · | +1.78 | · |
| `Neck_TrapeziousSize` | · | · | · | · | · | · | · | · | · | +0.10 | · |

### other

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Chest_Girth` | · | · | · | +7.40 | +0.74 | · | · | · | · | · | +0.26 |
| `Chest_SizeX` | · | · | · | +1.73 | · | · | · | · | · | · | -0.40 |
| `Chest_SizeY` | · | · | · | +6.35 | +0.43 | · | · | · | · | +0.58 | +3.42 |
| `Chest_SizeZ` | +3.51 | · | · | +0.31 | · | · | · | · | · | · | -0.41 |
| `Eyebrows_Angle` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyebrows_Droop` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyebrows_PosZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyebrows_Ridge` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyebrows_SizeY` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyebrows_Tone` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_Angle` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_Crease` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_InnerPosZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_LowerCurve` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_MiddlePosZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_OuterPosZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Eyelids_SizeZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_EarsNone` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_EarsPointRotation` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_EarsPointed` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_EarsPointedDown` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_EarsPointedUp` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_PupilCat` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_TeethOrc` | · | · | · | · | · | · | · | · | · | · | · |
| `Fantasy_TeethVampire` | · | · | · | · | · | · | · | · | · | · | · |

### pelvis

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Pelvis_Angle` | +0.14 | · | · | · | +1.89 | -0.39 | · | · | · | · | · |
| `Pelvis_CrotchDist` | · | · | · | · | · | · | · | · | · | · | · |
| `Pelvis_CrotchVolume` | · | · | · | · | · | · | · | · | · | · | · |
| `Pelvis_Girth` | · | · | +1.64 | · | +0.27 | +4.04 | · | · | · | · | · |
| `Pelvis_GluteusMass` | · | · | +2.17 | · | · | +14.70 | +0.08 | · | · | · | · |
| `Pelvis_GluteusSize` | · | · | +8.16 | · | +0.86 | +17.60 | +0.67 | · | · | · | · |
| `Pelvis_GluteusTone` | · | · | · | · | · | +0.82 | · | · | · | · | · |
| `Pelvis_Length` | +5.89 | · | · | · | · | · | · | · | · | · | · |
| `Pelvis_SizeX` | · | · | +3.06 | · | +0.40 | +6.12 | · | · | · | · | · |
| `Pelvis_SizeY` | · | · | · | · | · | +2.17 | · | · | · | · | · |

### shoulders

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Shoulders_Length` | · | +2.74 | · | +1.93 | · | · | · | · | · | +2.78 | +3.53 |
| `Shoulders_Mass` | · | +1.85 | · | +3.21 | · | · | · | · | · | +5.48 | +2.21 |
| `Shoulders_PosZ` | · | · | · | · | · | · | · | · | · | +0.23 | +0.25 |
| `Shoulders_Size` | · | +0.86 | · | +0.26 | · | · | · | · | · | +1.86 | +0.05 |
| `Shoulders_SizeX` | · | +5.38 | · | +2.13 | · | · | · | · | · | +4.94 | +4.96 |
| `Shoulders_SizeX2` | · | +2.98 | · | · | · | · | · | · | · | +2.64 | +2.21 |
| `Shoulders_Tone` | · | +1.45 | · | · | · | · | · | · | · | +3.85 | +1.34 |

### stomach

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Stomach_LocalFat` | · | · | · | +0.35 | +18.39 | · | · | · | · | · | · |
| `Stomach_Volume` | · | · | · | · | +6.18 | · | · | · | · | · | · |

### torso

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Torso_AureolaSize` | · | · | · | · | · | · | · | · | · | · | · |
| `Torso_BellyPosZ` | · | · | · | · | · | · | · | · | · | · | · |
| `Torso_Dorsi` | · | · | · | +6.08 | · | · | · | · | · | · | · |
| `Torso_Length` | +5.43 | · | · | · | -0.08 | · | · | · | · | · | · |
| `Torso_Mass` | · | +0.21 | +0.46 | +23.05 | +26.93 | +5.59 | +0.06 | · | · | +2.81 | +8.01 |
| `Torso_SizeX` | · | +3.40 | · | +6.64 | +6.53 | · | · | · | · | +1.01 | +0.09 |
| `Torso_SizeY` | · | · | · | +7.25 | +1.10 | · | · | · | · | +5.04 | +5.99 |
| `Torso_Tone` | · | · | · | +10.46 | -0.08 | · | · | · | · | +0.41 | +3.56 |
| `Torso_ToracicCurve` | · | · | · | +0.57 | · | · | · | · | · | +1.39 | +2.21 |
| `Torso_Vshape` | · | +4.72 | · | +9.37 | +3.08 | · | · | · | · | +4.32 | +2.35 |

### torso/breast

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Torso_BreastMass` | · | · | · | +1.15 | · | · | · | · | · | · | +0.10 |
| `Torso_BreastNipple` | · | · | · | · | · | · | · | · | · | · | · |
| `Torso_BreastPosX` | · | · | · | +2.69 | · | · | · | · | · | · | · |
| `Torso_BreastPosZ` | · | · | · | +0.12 | +0.07 | · | · | · | · | · | -0.17 |
| `Torso_BreastScaleY` | · | · | · | +4.09 | · | · | · | · | · | · | +0.07 |
| `Torso_BreastTone` | · | · | · | · | · | · | · | · | · | · | · |

### waist

| slider | stature | shldr | hipW | bust | waist | hip | thigh | knee | calf | uArm | fArm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Waist_Size` | · | · | · | · | +8.39 | · | · | · | · | · | · |