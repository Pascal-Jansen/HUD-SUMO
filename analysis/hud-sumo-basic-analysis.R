library("rstudioapi")
setwd(dirname(getActiveDocumentContext()$path))

library(devtools)
source_url("https://raw.githubusercontent.com/M-Colley/rCode/main/r_functionality.R")

library(DataExplorer)

main_df = NULL

# Construct the file path
file_path <- "../sample_data/Town01_21-23-53_2024-10-08_simulation_data.csv"

# Read the CSV file
main_df <- read_delim(file_path, delim = ",")

main_df <- as.data.frame(main_df)
names(main_df)

# create a basic report of all the data
DataExplorer::create_report(main_df, output_file = paste0("test_report.html"))



main_df$map <- as.factor(main_df$map)
main_df$vehicle_id <- as.factor(main_df$vehicle_id)
main_df$hud_id <- as.factor(main_df$hud_id)
main_df$vehicle_type <- as.factor(main_df$vehicle_type) # hud dependent on type

# HUD-related
main_df$brightness <- as.factor(main_df$brightness)
main_df$information_frequency <- as.factor(main_df$information_frequency)
main_df$information_relevance <- as.factor(main_df$information_relevance)
main_df$FoV <- as.factor(main_df$FoV)

# calculated levels
#main_df$awarenessLevel
#main_df$fatiguenessLevel
#main_df$reactionTime
#main_df$minGapFactor
#main_df$speedAdherenceFactor
#main_df$maxSpeed
#main_df$acceleration

# checking 
levels(main_df$hud_id)

# Basic analysis of Acceleration (current_acceleration)
checkAssumptionsForAnova(data = main_df, y = "current_acceleration", factors = c("hud_id"))

# todo: requires at least two maps
modelArt <- art(current_acceleration ~  hud_id + Error(vehicle_id / (hud_id)), data = main_df) |> anova()
modelArt
reportART(modelArt, dv = "current acceleration")



# Basic analysis of Gap (current_gap)


# Basic analysis of Speed (current_speed) # not working currently
checkAssumptionsForAnova(data = main_df, y = "current_speed", factors = c("map", "hud_id"))

# todo: requires at least two maps
modelArt <- art(current_speed ~ map * hud_id + Error(vehicle_id / (map * hud_id)), data = main_df) |> anova()
modelArt
reportART(modelArt, dv = "current speed")

##dunnTest(current_speed ~ hud_id, data = main_df, method = "holm") |> reportDunnTest(data = main_df, iv = "hud_id", dv = "current_speed")






