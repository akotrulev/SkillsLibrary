"use client";

import { createTheme } from "@mui/material/styles";

/**
 * Dark, dense, control-room styling: this is an operations board that stays
 * open for long stretches, so contrast and information density matter more
 * than decoration.
 */
export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: "dark",
    background: { default: "#0d1117", paper: "#151b23" },
    primary: { main: "#4c8dff" },
    secondary: { main: "#b184ff" },
    success: { main: "#3fb950" },
    warning: { main: "#d29922" },
    error: { main: "#f85149" },
    info: { main: "#58a6ff" },
    divider: "rgba(240,246,252,0.12)",
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily:
      'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h1: { fontSize: "1.5rem", fontWeight: 650, letterSpacing: "-0.01em" },
    h2: { fontSize: "1.125rem", fontWeight: 650 },
    body2: { fontSize: "0.8125rem" },
    caption: { fontSize: "0.75rem" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { scrollbarColor: "rgba(240,246,252,0.2) transparent" },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { textTransform: "none", fontWeight: 600 } },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 600 } } },
    MuiPaper: { defaultProps: { elevation: 0 } },
  },
});
