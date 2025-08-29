import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

def to_bool_yes_no(x):
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ["yes", "y", "si", "sí", "true", "1"]:
            return 1
        if s in ["no", "n", "false", "0"]:
            return 0
    if isinstance(x, (int, float)):
        return 1 if x else 0
    return np.nan

def generate_pdf_report(outdir, overall_accuracy, acc_by_object, acc_by_user, acc_by_cond, summary_df, notes_sample=None):
    pdf_path = os.path.join(outdir, "analysis_report.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Título
    story.append(Paragraph("LUCIA - Validation Report", styles['Title']))
    story.append(Paragraph(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Métricas resumen
    story.append(Paragraph("<b>Métricas resumen</b>", styles['Heading2']))
    story.append(Paragraph(f"Precisión global: {overall_accuracy:.2f} %", styles['Normal']))
    story.append(Spacer(1, 8))

    # Pequeña tabla resumen (desde summary_df)
    tbl_data = [list(summary_df.columns)] + summary_df.values.tolist()
    story.append(Table(tbl_data))
    story.append(Spacer(1, 12))

    # Precisión por objeto
    story.append(Paragraph("<b>Precisión por objeto</b>", styles['Heading3']))
    data_obj = [["Object", "Accuracy (%)", "N"]] + [[str(idx), f"{row['Accuracy_%']:.2f}", int(row['N'])] for idx, row in acc_by_object.reset_index().iterrows()]
    story.append(Table(data_obj))
    story.append(Spacer(1, 12))

    # Precisión por usuario
    story.append(Paragraph("<b>Precisión por usuario</b>", styles['Heading3']))
    data_user = [["User", "Accuracy (%)", "N"]] + [[str(idx), f"{row['Accuracy_%']:.2f}", int(row['N'])] for idx, row in acc_by_user.reset_index().iterrows()]
    story.append(Table(data_user))
    story.append(Spacer(1, 12))

    # Precisión por condición de imagen
    story.append(Paragraph("<b>Precisión por condición de imagen (primeras filas)</b>", styles['Heading3']))
    acc_by_cond_top = acc_by_cond.reset_index().head(20)
    data_cond = [["Condition", "Accuracy (%)", "N"]] + [
        [str(idx), f"{row['Accuracy_%']:.2f}", int(row['N'])]
        for idx, row in acc_by_cond_top.iterrows()
    ]
    story.append(Table(data_cond))
    story.append(Spacer(1, 12))

    # Insertar gráficos si existen
    story.append(Paragraph("<b>Gráficos</b>", styles['Heading2']))
    charts = [
        "plot_accuracy_by_object.png",
        "plot_accuracy_by_user.png",
        "plot_accuracy_by_condition.png",
        "plot_confidence_hist_detected.png",
        "plot_confidence_by_object_boxplot.png"
    ]
    for g in charts:
        p = os.path.join(outdir, g)
        if os.path.exists(p):
            try:
                story.append(Image(p, width=450, height=260))
                story.append(Spacer(1, 12))
            except Exception as e:
                story.append(Paragraph(f"No se pudo incrustar la imagen {g}: {e}", styles['Normal']))

    # Opcional: incluir una muestra de notas de usuario si se proporciona
    if notes_sample is not None and len(notes_sample) > 0:
        story.append(Paragraph("<b>Muestra de notas de usuario</b>", styles['Heading2']))
        for note in notes_sample[:10]:
            txt = note if isinstance(note, str) else str(note)
            story.append(Paragraph(txt, styles['Normal']))
            story.append(Spacer(1, 6))

    doc.build(story)
    print(f" Informe PDF guardado en {pdf_path}")

def main(input_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = pd.read_excel(input_path)
    df.columns = [c.strip() for c in df.columns]

    expected = ["Users", "Object", "Image Conditions", "Attempts", "Detected", "Confidence", "Notes"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        print(f"WARNING: faltan columnas en el Excel: {missing}")

    # Normalizar
    df["Detected_bool"] = df["Detected"].apply(to_bool_yes_no)
    df["Users"] = df["Users"].astype(str).str.strip()
    df["Attempts"] = pd.to_numeric(df["Attempts"], errors="coerce")
    df["Confidence"] = pd.to_numeric(df["Confidence"], errors="coerce")

    # Métricas resumen
    n_rows = len(df)
    n_detected = int(df["Detected_bool"].sum(skipna=True))
    overall_accuracy = df["Detected_bool"].mean(skipna=True) * 100 if n_rows else np.nan
    avg_attempts = df["Attempts"].mean(skipna=True)
    avg_conf_all = df["Confidence"].mean(skipna=True)
    avg_conf_detected = df.loc[df["Detected_bool"] == 1, "Confidence"].mean(skipna=True)

    summary = pd.DataFrame({
        "Metric": [
            "Total rows",
            "Detected YES count",
            "Overall accuracy (%)",
            "Average attempts (all)",
            "Average confidence (all rows)",
            "Average confidence (detected=YES)",
        ],
        "Value": [
            n_rows,
            n_detected,
            round(overall_accuracy, 2) if pd.notna(overall_accuracy) else None,
            round(avg_attempts, 3) if pd.notna(avg_attempts) else None,
            round(avg_conf_all, 3) if pd.notna(avg_conf_all) else None,
            round(avg_conf_detected, 3) if pd.notna(avg_conf_detected) else None,
        ]
    })

    # Métricas agrupadas
    acc_by_object = (df.groupby("Object")["Detected_bool"].mean() * 100).sort_values(ascending=False).to_frame("Accuracy_%")
    acc_by_object = acc_by_object.join(df.groupby("Object")["Detected_bool"].count().to_frame("N"))

    acc_by_user = (df.groupby("Users")["Detected_bool"].mean() * 100).sort_values(ascending=False).to_frame("Accuracy_%")
    acc_by_user = acc_by_user.join(df.groupby("Users")["Detected_bool"].count().to_frame("N"))

    acc_by_cond = (df.groupby("Image Conditions")["Detected_bool"].mean() * 100).sort_values(ascending=False).to_frame("Accuracy_%")
    acc_by_cond = acc_by_cond.join(df.groupby("Image Conditions")["Detected_bool"].count().to_frame("N"))

    attempts_by_object = df.groupby("Object")["Attempts"].agg(["mean", "std", "count"]).rename(columns={"mean": "Attempts_mean", "std": "Attempts_std", "count": "N"})
    conf_by_object = df.loc[df["Detected_bool"] == 1].groupby("Object")["Confidence"].agg(["mean", "std", "count"]).rename(columns={"mean": "Confidence_mean", "std": "Confidence_std", "count": "N_detected"})

    # Guardar CSVs
    summary.to_csv(os.path.join(out_dir, "summary_metrics.csv"), index=False)
    acc_by_object.to_csv(os.path.join(out_dir, "accuracy_by_object.csv"))
    acc_by_user.to_csv(os.path.join(out_dir, "accuracy_by_user.csv"))
    acc_by_cond.to_csv(os.path.join(out_dir, "accuracy_by_condition.csv"))
    attempts_by_object.to_csv(os.path.join(out_dir, "attempts_by_object.csv"))
    conf_by_object.to_csv(os.path.join(out_dir, "confidence_by_object_detected_only.csv"))

    # Gráficos
    plt.figure()
    acc_by_object["Accuracy_%"].plot(kind="bar")
    plt.ylabel("Accuracy (%)")
    plt.title("Accuracy by Object")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plot_accuracy_by_object.png"))
    plt.close()

    plt.figure()
    acc_by_user["Accuracy_%"].plot(kind="bar")
    plt.ylabel("Accuracy (%)")
    plt.title("Accuracy by User")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plot_accuracy_by_user.png"))
    plt.close()

    acc_by_cond_plot = acc_by_cond.copy()
    if len(acc_by_cond_plot) > 15:
        acc_by_cond_plot = acc_by_cond_plot.head(15)
    plt.figure()
    acc_by_cond_plot["Accuracy_%"].plot(kind="bar")
    plt.ylabel("Accuracy (%)")
    plt.title("Accuracy by Image Condition (Top 15)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "plot_accuracy_by_condition.png"))
    plt.close()

    conf_detected = df.loc[df["Detected_bool"] == 1, "Confidence"].dropna()
    if not conf_detected.empty:
        plt.figure()
        plt.hist(conf_detected, bins=15)
        plt.xlabel("Confidence")
        plt.ylabel("Count")
        plt.title("Confidence Distribution (Detected = YES)")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "plot_confidence_hist_detected.png"))
        plt.close()

    if df.loc[df["Detected_bool"] == 1, "Object"].nunique() >= 2:
        plt.figure()
        data = [grp["Confidence"].dropna().values for _, grp in df.loc[df["Detected_bool"] == 1].groupby("Object")]
        labels = [name for name, _ in df.loc[df["Detected_bool"] == 1].groupby("Object")]
        try:
            plt.boxplot(data, tick_labels=labels, vert=True, showmeans=True)
        except TypeError:
            plt.boxplot(data, labels=labels, vert=True, showmeans=True)
        plt.ylabel("Confidence")
        plt.title("Confidence by Object (Detected = YES)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "plot_confidence_by_object_boxplot.png"))
        plt.close()

    print(" Análisis completado. Resultados en:", out_dir)

    # Generar informe PDF usando las variables calculadas
    # pasar una pequeña muestra de notas para inclusión (opcional)
    notes_sample = df["Notes"].dropna().astype(str).tolist() if "Notes" in df.columns else None
    generate_pdf_report(out_dir, overall_accuracy, acc_by_object, acc_by_user, acc_by_cond, summary, notes_sample)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="TestsResults.xlsx", help="Ruta al fichero Excel")
    parser.add_argument("--outdir", default="reports", help="Carpeta de salida")
    args = parser.parse_args()
    main(args.input, args.outdir)
