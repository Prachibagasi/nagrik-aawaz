"""Architecture diagram helpers used by the recruitment pipeline demo."""

from pathlib import Path


class DiagramGenerator:
    """Write a small diagram of the resume-screening agent pipeline."""

    @staticmethod
    def save_mermaid_diagram(output_path="agent_diagram.md"):
        diagram = """```mermaid
flowchart LR
    JD[JD Summarizer] --> Match[Matcher]
    CV[CV Extractor] --> Match
    Match --> Shortlist[Shortlister]
    Shortlist --> Email[Interview Scheduler]
    JD -. persist .-> DB[(SQLite Memory)]
    CV -. persist .-> DB
    Match -. persist .-> DB
    Shortlist -. persist .-> DB
``` 
"""
        path = Path(output_path)
        path.write_text(diagram, encoding="utf-8")
        return str(path)

    @staticmethod
    def generate_matplotlib_diagram(output_path="agent_diagram.png"):
        import matplotlib.pyplot as plt

        labels = ["JD Summarizer", "CV Extractor", "Matcher", "Shortlister", "Interview Scheduler"]
        positions = [(0, 1), (0, -1), (2, 0), (4, 0), (6, 0)]
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.set_axis_off()
        for label, (x, y) in zip(labels, positions):
            ax.text(
                x,
                y,
                label,
                ha="center",
                va="center",
                bbox={"boxstyle": "round,pad=0.6", "facecolor": "#e8f1ff", "edgecolor": "#2563eb"},
            )

        for start, end in [((0.65, 0.85), (1.35, 0.2)), ((0.65, -0.85), (1.35, -0.2)),
                           ((2.65, 0), (3.35, 0)), ((4.65, 0), (5.35, 0))]:
            ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "color": "#475569"})

        ax.set_xlim(-1.3, 7.3)
        ax.set_ylim(-1.8, 1.8)
        path = Path(output_path)
        fig.savefig(path, bbox_inches="tight", dpi=160)
        plt.close(fig)
        return str(path)
