/**
 * Salida de un track (SPEC 8, 11.5).
 *
 * Un score de simulación se rotula como simulación y nunca como probabilidad
 * clínica. Una abstención se presenta como salida válida, sin banda ni narrativa
 * de riesgo.
 */

import { AbstainedState } from "@/components/States";
import type { PredictionOutputView } from "@/lib/contracts";
import { TEXTS } from "@/lib/texts";

const TRACK_LABELS: Record<string, string> = {
  synthetic_reference_v021: "Referencia de simulación",
  real_personal_baseline_v1: "Estadística personal",
};

export function PredictionOutputCard({ output }: { output: PredictionOutputView }) {
  const label = TRACK_LABELS[output.track_id] ?? output.track_id;
  const isSimulation = output.intended_use === "simulation_only";

  if (output.status !== "ok") {
    return (
      <section aria-label={label} data-track={output.track_id} className="space-y-2">
        <h3 className="text-sm font-semibold text-ink">{label}</h3>
        <AbstainedState reasons={output.abstention_reasons} />
        <p className="faro-hint">Versión del modelo: {output.model_version}</p>
      </section>
    );
  }

  return (
    <section aria-label={label} data-track={output.track_id} className="faro-card space-y-2">
      <h3 className="text-sm font-semibold text-ink">{label}</h3>
      {isSimulation ? (
        <>
          <p className="inline-flex items-center gap-2 rounded bg-canvas px-2 py-1 text-xs font-semibold text-caution">
            <span aria-hidden="true">◈</span>
            {TEXTS.simulationBadge}
          </p>
          <p className="text-2xl font-semibold tabular-nums text-ink">
            {output.simulation_score?.toFixed(2)}
          </p>
          <p className="faro-hint">{TEXTS.simulationHelp}</p>
        </>
      ) : (
        <>
          <p className="text-2xl font-semibold tabular-nums text-ink">
            {output.probability === null ? "—" : `${(output.probability * 100).toFixed(0)}%`}
          </p>
          {output.interval ? (
            <p className="faro-hint">
              Intervalo {output.interval_method ?? ""}: {(output.interval[0] * 100).toFixed(0)}%
              {" – "}
              {(output.interval[1] * 100).toFixed(0)}%
            </p>
          ) : null}
        </>
      )}
      <dl className="grid grid-cols-2 gap-1 text-xs text-muted">
        <dt>Uso previsto</dt>
        <dd>{output.intended_use}</dd>
        <dt>Tipo de estimación</dt>
        <dd>{output.estimate_kind}</dd>
        <dt>Origen de los datos</dt>
        <dd>{output.input_data_origin}</dd>
        <dt>Versión del modelo</dt>
        <dd>{output.model_version}</dd>
      </dl>
    </section>
  );
}
