"""
Function that takes the information_relevance, information_frequency and fov of the HUD settings and the calculated
distraction_level (calc_distraction) and fatigueness_level (calc_fatigueness) and calculates the awareness_level.
The return value is an int between 1 and 10.

-https://ieeexplore.ieee.org/document/10199531
-https://ieeexplore.ieee.org/document/8943689

"""
def calc_awareness(information_relevance, information_frequency, distraction_level, fatigueness_level, fov):
    base_awareness = 5  

    weight_relevance = 0.9
    weight_frequency = 0.8
    weight_distraction = 0.6
    weight_fatigueness = 0.4
    weight_fov = 0.4

    relevance_effect = {
        "unimportant": 0 * weight_relevance,  
        "neutral": 1 * weight_relevance,       
        "important": 3 * weight_relevance       
    }

    frequency_effect = {
        "minimum": 2 * weight_frequency,      
        "average": 1 * weight_frequency,      
        "maximum": 0 * weight_frequency       
    }

    distraction_effect = distraction_level * weight_distraction  
    fatigueness_effect = fatigueness_level * weight_fatigueness  

    fov_effect = {
        "small": 0 * weight_fov,             
        "medium": 2 * weight_fov,              
        "large": 1 * weight_fov                 
    }
    
    total_effect = (
        relevance_effect.get(information_relevance, 0) +
        frequency_effect.get(information_frequency, 0) +
        fov_effect.get(fov, 0) +
        (distraction_effect - fatigueness_effect)
    )

    awareness_level = base_awareness * (total_effect/3) 

    return int(awareness_level)


"""
Function that takes the information_relevance, information_frequency, brightness and fov of the HUD settings 
and calculates the distraction_level.
The return value is an int between 1 and 10.

-https://www.sciencedirect.com/science/article/pii/S1369847815000741
-https://ieeexplore.ieee.org/document/8917472
"""
def calc_distraction(information_relevance, information_frequency, brightness, fov):

    base_distraction = 6

    # Gewichtungen für die Einflussfaktoren
    weight_relevance = 0.9
    weight_frequency = 0.8
    weight_brightness = 0.4 
    weight_fov = 0.3

    # Einflussfaktoren
    relevance_effect = {
        "unimportant": 3 * weight_relevance,  
        "neutral": 2 * weight_relevance,      
        "important": 0 * weight_relevance    
    }

    frequency_effect = {
        "minimum": 1 * weight_frequency,      
        "average": 2 * weight_frequency,      
        "maximum": 3 * weight_frequency        
    }

    brightness_effect = {
        "very dark": 3 * weight_brightness,    
        "dark": 0 * weight_brightness,        
        "average": 1 * weight_brightness,     
        "bright": 2 * weight_brightness,     
        "very bright": 2 * weight_brightness  
    }

    fov_effect = {
        "small": 2 * weight_fov,        
        "medium": 0 * weight_fov,       
        "large": 3 * weight_fov          
    }

    total_effect = (relevance_effect.get(information_relevance, 0)  +
                    frequency_effect.get(information_frequency, 0) +
                    fov_effect.get(fov, 0) +
                    brightness_effect.get(brightness, 0)
                    ) 
    
    distraction_level = total_effect * (base_distraction/ 4)

    return int(distraction_level) 


"""
Function that takes the information_relevance, information_frequency and brightness of the HUD settings 
and calculates the fatigueness_level.
The return value is an int between 1 and 10.

-https://www.sciencedirect.com/science/article/pii/S1877042814001311
-https://www.sciencedirect.com/science/article/pii/S0001457505000114
"""
def calc_fatigueness(information_relevance, information_frequency, brightness):
    
    base_fatigueness = 5

    weight_relevance = 0.8 
    weight_frequency = 0.9  
    weight_brightness = 0.4     

    relevance_effect = {
        "unimportant": 3 * weight_relevance,  
        "neutral": 2 * weight_relevance,       
        "important": 0 * weight_relevance     
    }

    frequency_effect = {
        "minimum": 1 * weight_frequency,        
        "average": 2 * weight_frequency,        
        "maximum": 3 * weight_frequency          
    }

    brightness_effect = {
        "very dark": 1 * weight_brightness,     
        "dark": 0 * weight_brightness,          
        "average": 1 * weight_brightness,       
        "bright": 2 * weight_brightness,       
        "very bright": 3 * weight_brightness    
    }

    total_effect = (relevance_effect.get(information_relevance, 0) +
                    frequency_effect.get(information_frequency, 0) +
                    brightness_effect.get(brightness, 0))

    fatigue_level = base_fatigueness * (total_effect/3)  

    return int(fatigue_level)


"""
Function that takes the calculated distraction_level, fatigueness_level and awareness_level 
and calculates the reaction time.

-https://www.sciencedirect.com/science/article/pii/S0141938204000022
-https://onlinelibrary.wiley.com/doi/full/10.4218/etrij.16.0115.0770
"""
def calc_ReactTime(distraction_level, fatigueness_level, awareness_level):
    base_time = 0.9

    distraction_effect = 0.6 * distraction_level 
    fatigueness_effect = 0.2 * fatigueness_level
    awareness_effect = 0.7 * awareness_level  
    
    react_time = base_time + ((distraction_effect + fatigueness_effect)**0.3-(awareness_effect ** 0.4))/3

    return react_time


"""
Function that takes the calculated distraction_level, fatigueness_level and awareness_level and 
the fov of the HUD settings and calculates the minimal gap factor. 

-https://www.sciencedirect.com/science/article/pii/S1071581923000691
"""
def calc_MinGap(distraction_level, fatigueness_level, awareness_level, field_of_view):
    base_min_gap = 1.4
    weight_fov = 0.3

    distraction_effect = 0.6 * distraction_level  
    fatigueness_effect = 0.2 * fatigueness_level  
    awareness_effect = 0.9 * awareness_level    
    
    fov_effect = {
        "small": 0 * weight_fov,             
        "medium": 2 * weight_fov,              
        "large": 1 * weight_fov                 
    }

    min_gap_factor = base_min_gap + ((awareness_effect ** 0.2 - (distraction_effect + fatigueness_effect)/2 + fov_effect.get(field_of_view, 0)))/3

    return min_gap_factor


"""
Function that takes the calculated distraction_level, fatigueness_level and awareness_level 
and the fov, information_relevance and information_frequency and calculates the speed adherence factor.

-https://www.sciencedirect.com/science/article/pii/S0003687023001850
-https://www.sciencedirect.com/science/article/pii/S1071581923000691
"""
def calc_SpeedAd(fov, distraction_level, fatigueness_level, awareness_level, information_relevance, frequency):

    base_SpeedAd = 0.95 

    weight_relevance = 0.7
    weight_distraction = 0.9
    weight_fatigueness = 0.4
    weight_fov = 0.4
    weight_awareness = 0.8
    weight_frequency = 0.6

    relevance_effect = {
        "unimportant": 2 * weight_relevance,  
        "neutral": 0 * weight_relevance,       
        "important": 1 * weight_relevance       
    }

    distraction_effect = (distraction_level * weight_distraction) ** 1.2  
    fatigueness_effect = (fatigueness_level * weight_fatigueness)/2 
    awareness_effect = (awareness_level * weight_awareness)

    fov_effect = {
        "small": 0 * weight_fov,             
        "medium": 2 * weight_fov,              
        "large": 1 * weight_fov                 
    }

    frequency_effect = {
        "minimum": 3 * weight_frequency,      
        "average": 2 * weight_frequency,      
        "maximum": 1 * weight_frequency        
    }

    total_effect = (
        relevance_effect.get(information_relevance, 0) **0.8 +
        fov_effect.get(fov, 0) + distraction_effect + awareness_effect + fatigueness_effect + frequency_effect.get(frequency, 0)
    )

    speedAd = (base_SpeedAd * (total_effect/6))/2

    return float(speedAd)


"""
Function that takes the calculated distraction_level, fatigueness_level and awareness_level 
and the information_frequency of the HUD settings and calculates the maximal speed.

-https://ieeexplore.ieee.org/document/9536587
-https://www.sciencedirect.com/science/article/pii/S0003687023001850
"""
def calc_MaxSpeed(awareness_level, fatigueness_level, distraction_level, frequency):
    
    base_speed = 150

    weight_awareness = 0.9
    weight_fatigueness = 0.4
    weight_distraction = 0.3
    weight_frequency = 0.2

    awareness_effect = awareness_level * weight_awareness  
    fatigueness_effect = fatigueness_level * weight_fatigueness 
    distraction_effect = distraction_level * weight_distraction

    frequency_effect = {
        "minimum": 1 * weight_frequency,        
        "average": 2 * weight_frequency,        
        "maximum": 3 * weight_frequency          
    }

    max_speed = (base_speed * (awareness_effect + fatigueness_effect + distraction_effect + frequency_effect.get(frequency, 0)))/10
    return int(max_speed) 


"""
Function that takes the calculated distraction_level, fatigueness_level and awareness_level 
and the information_relevance of the HUD settings and calculates the acceleration.

-https://www.sciencedirect.com/science/article/pii/S1071581904000497
-https://ieeexplore.ieee.org/document/9536587
"""
def calc_acceleration(fatigueness_level, distraction_level, awareness_level, relevance):
    
    base_acceleration = 6.5

    weight_relevance = 0.6
    
    awareness_effect = 0.8 * awareness_level
    fatigueness_effect = 0.2 * fatigueness_level
    distraction_effect = 0.5 * distraction_level

    relevance_effect = {
        "unimportant": 2 * weight_relevance,  
        "neutral": 0 * weight_relevance,       
        "important": 1 * weight_relevance       
    }
    
    acceleration = (base_acceleration * (awareness_effect + fatigueness_effect + distraction_effect + relevance_effect.get(relevance, 0)))/10
    
    return acceleration

