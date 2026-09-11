#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(readxl)
  library(ggplot2)
  library(tidyr)
  library(dplyr)
})

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || is.na(x)) y else x

args <- commandArgs(trailingOnly = FALSE)
file_arg <- args[grepl("^--file=", args)]
script_path <- sub("^--file=", "", file_arg[1] %||% "code/problem1/plot_problem1_figures.R")
repo_root <- normalizePath(file.path(dirname(script_path), "..", ".."), mustWork = FALSE)
if (!dir.exists(file.path(repo_root, "results", "problem1"))) {
  repo_root <- normalizePath(getwd(), mustWork = TRUE)
}

input_xlsx <- file.path(repo_root, "results", "problem1", "result1.xlsx")
output_dir <- file.path(repo_root, "results", "problem1", "figures")
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

selected_times <- c(100, 600, 1200, 1800)
line_colors <- c(
  "100 s" = "#0072B2",
  "600 s" = "#E69F00",
  "1200 s" = "#009E73",
  "1800 s" = "#D55E00"
)
line_types <- c("100 s" = "solid", "600 s" = "dashed", "1200 s" = "dotdash", "1800 s" = "twodash")

read_profile_sheet <- function(sheet_index) {
  raw <- read_excel(input_xlsx, sheet = sheet_index, .name_repair = "minimal")
  names(raw)[1] <- "time_s"

  raw |>
    filter(time_s %in% selected_times) |>
    pivot_longer(-time_s, names_to = "radius_cm", values_to = "value") |>
    mutate(
      time_label = factor(paste0(time_s, " s"), levels = paste0(selected_times, " s")),
      radius_cm = as.numeric(radius_cm),
      value = as.numeric(value)
    ) |>
    arrange(time_s, radius_cm)
}

save_plot <- function(plot, basename) {
  png_path <- file.path(output_dir, paste0(basename, ".png"))
  pdf_path <- file.path(output_dir, paste0(basename, ".pdf"))

  ggsave(png_path, plot, width = 6.7, height = 3.8, units = "in", dpi = 600, bg = "white")
  ggsave(pdf_path, plot, width = 6.7, height = 3.8, units = "in", device = cairo_pdf, bg = "white")

  message("Saved: ", png_path)
  message("Saved: ", pdf_path)
}

base_theme <- theme_bw(base_size = 10, base_family = "Times New Roman") +
  theme(
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(linewidth = 0.25, colour = "grey86"),
    legend.position = "right",
    legend.background = element_blank(),
    legend.title = element_blank(),
    axis.title = element_text(size = 10),
    axis.text = element_text(size = 9, colour = "black"),
    plot.title = element_text(size = 11, face = "bold", hjust = 0),
    plot.subtitle = element_text(size = 9, hjust = 0, colour = "grey25"),
    plot.margin = margin(6, 8, 6, 6)
  )

temperature <- read_profile_sheet(1)
moisture <- read_profile_sheet(2)

temp_plot <- ggplot(temperature, aes(x = radius_cm, y = value, colour = time_label, linetype = time_label)) +
  geom_line(linewidth = 0.85) +
  geom_point(size = 1.35, stroke = 0.2) +
  scale_colour_manual(values = line_colors) +
  scale_linetype_manual(values = line_types) +
  scale_x_continuous(breaks = seq(0, 2, by = 0.5), limits = c(0, 2), expand = expansion(mult = c(0.01, 0.02))) +
  scale_y_continuous(expand = expansion(mult = c(0.03, 0.06))) +
  labs(
    title = "Problem 1: radial temperature profiles during preheating",
    subtitle = "The surface heats first and the thermal disturbance moves inward",
    x = "Distance from center / cm",
    y = "Temperature / deg C"
  ) +
  base_theme

moist_plot <- ggplot(moisture, aes(x = radius_cm, y = value, colour = time_label, linetype = time_label)) +
  geom_line(linewidth = 0.85) +
  geom_point(size = 1.35, stroke = 0.2) +
  scale_colour_manual(values = line_colors) +
  scale_linetype_manual(values = line_types) +
  scale_x_continuous(breaks = seq(0, 2, by = 0.5), limits = c(0, 2), expand = expansion(mult = c(0.01, 0.02))) +
  scale_y_continuous(expand = expansion(mult = c(0.03, 0.06))) +
  labs(
    title = "Problem 1: radial moisture profiles during preheating",
    subtitle = "Moisture loss is concentrated near the surface within 30 min",
    x = "Distance from center / cm",
    y = "Moisture content / kg kg^-1"
  ) +
  base_theme

save_plot(temp_plot, "problem1_temperature_radial_profiles")
save_plot(moist_plot, "problem1_moisture_radial_profiles")
