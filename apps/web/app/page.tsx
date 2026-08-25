import Link from "next/link";

export default function HomePage() {
  return (
    <section className="space-y-4">
      <div className="faro-card space-y-2">
        <h1 className="text-lg font-semibold text-ink">Demo local de Faro v0.3.0</h1>
        <p className="text-sm text-ink">
          Esta demostración corre contra una base local con datos ficticios. Faro organiza
          registros, calcula estadísticas personales, muestra estimaciones experimentales y
          ofrece apoyos previamente curados para revisión profesional.
        </p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
          <li>No diagnostica ni prescribe.</li>
          <li>No reemplaza el criterio profesional.</li>
          <li>No afirma eficacia causal a partir de feedback observacional.</li>
        </ul>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Link href="/cuidador" className="faro-card hover:bg-canvas">
          <p className="font-semibold text-ink">Cuidador</p>
          <p className="faro-hint">Registro del día, resultado pendiente y apoyos aprobados.</p>
        </Link>
        <Link href="/profesional" className="faro-card hover:bg-canvas">
          <p className="font-semibold text-ink">Profesional</p>
          <p className="faro-hint">Inbox de recomendaciones, revisión y aplicación.</p>
        </Link>
        <Link href="/evaluacion" className="faro-card hover:bg-canvas">
          <p className="font-semibold text-ink">Evaluación</p>
          <p className="faro-hint">Reportes versionados con origen y limitaciones.</p>
        </Link>
      </div>
    </section>
  );
}
