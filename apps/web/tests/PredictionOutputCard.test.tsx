/**
 * Separación visible entre simulación, estadística personal y abstención.
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PredictionOutputCard } from "@/components/PredictionOutputCard";
import { abstainedBaseline, simulationScore } from "./fixtures";

describe("PredictionOutputCard", () => {
  it("rotula el score de simulación y niega que sea una probabilidad clínica", () => {
    render(<PredictionOutputCard output={simulationScore()} />);
    expect(screen.getByText("Simulación")).toBeInTheDocument();
    expect(screen.getByText("0.42")).toBeInTheDocument();
    expect(screen.getByText(/No es una probabilidad clínica/)).toBeInTheDocument();
  });

  it("una abstención no muestra banda ni narrativa de riesgo", () => {
    render(<PredictionOutputCard output={abstainedBaseline()} />);
    expect(screen.getByText(/Faro se abstiene/)).toBeInTheDocument();
    expect(screen.queryByText(/verde|ámbar|rojo|riesgo alto/i)).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("muestra track, uso previsto y versión del modelo", () => {
    render(<PredictionOutputCard output={simulationScore()} />);
    expect(screen.getByText("simulation_only")).toBeInTheDocument();
    expect(screen.getByText("synthetic-reference-mock-0.2.1")).toBeInTheDocument();
  });
});
