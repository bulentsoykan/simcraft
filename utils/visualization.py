"""
Visualization utilities for simulation results.

Provides plotting functions for common simulation outputs.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from simcraft.statistics.time_series import TimeSeries
    from simcraft.statistics.tally import Tally


def plot_time_series(
    time_series: "TimeSeries",
    title: Optional[str] = None,
    xlabel: str = "Time",
    ylabel: str = "Value",
    figsize: Tuple[int, int] = (10, 6),
    show: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Plot a time series.

    Parameters
    ----------
    time_series : TimeSeries
        Time series to plot
    title : Optional[str]
        Plot title
    xlabel : str
        X-axis label
    ylabel : str
        Y-axis label
    figsize : Tuple[int, int]
        Figure size
    show : bool
        Whether to show the plot
    save_path : Optional[str]
        Path to save figure

    Returns
    -------
    Any
        Matplotlib figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for visualization")

    history = time_series.get_history()
    if not history:
        raise ValueError("No history data to plot")

    times = [t for t, _ in history]
    values = [v for _, v in history]

    fig, ax = plt.subplots(figsize=figsize)
    ax.step(times, values, where="post", linewidth=1.5)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or time_series.name)
    ax.grid(True, alpha=0.3)

    # Add statistics annotation
    stats_text = (
        f"Average: {time_series.average_value:.2f}\n"
        f"Max: {time_series.max_value:.2f}\n"
        f"Min: {time_series.min_value:.2f}"
    )
    ax.text(
        0.02,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)

    if show:
        plt.show()

    return fig


def plot_histogram(
    tally: "Tally",
    bins: int = 20,
    title: Optional[str] = None,
    xlabel: str = "Value",
    ylabel: str = "Frequency",
    figsize: Tuple[int, int] = (10, 6),
    show: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Plot histogram from tally data.

    Parameters
    ----------
    tally : Tally
        Tally with history
    bins : int
        Number of bins
    title : Optional[str]
        Plot title
    xlabel : str
        X-axis label
    ylabel : str
        Y-axis label
    figsize : Tuple[int, int]
        Figure size
    show : bool
        Whether to show plot
    save_path : Optional[str]
        Path to save figure

    Returns
    -------
    Any
        Matplotlib figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for visualization")

    history = tally.get_history()
    if not history:
        raise ValueError("No history data to plot")

    values = [v for _, v in history]

    fig, ax = plt.subplots(figsize=figsize)
    ax.hist(values, bins=bins, edgecolor="black", alpha=0.7)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title or tally.name)
    ax.grid(True, alpha=0.3, axis="y")

    # Add statistics
    stats_text = (
        f"Count: {tally.count}\n"
        f"Mean: {tally.mean:.2f}\n"
        f"Std: {tally.std:.2f}"
    )
    ax.text(
        0.98,
        0.98,
        stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment="top",
        horizontalalignment="right",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)

    if show:
        plt.show()

    return fig


def plot_multiple_series(
    series_list: List[Tuple[str, "TimeSeries"]],
    title: str = "Time Series Comparison",
    xlabel: str = "Time",
    ylabel: str = "Value",
    figsize: Tuple[int, int] = (12, 6),
    show: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Plot multiple time series on same axes.

    Parameters
    ----------
    series_list : List[Tuple[str, TimeSeries]]
        List of (label, time_series) tuples
    title : str
        Plot title
    xlabel : str
        X-axis label
    ylabel : str
        Y-axis label
    figsize : Tuple[int, int]
        Figure size
    show : bool
        Whether to show plot
    save_path : Optional[str]
        Save path

    Returns
    -------
    Any
        Matplotlib figure
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError("matplotlib is required for visualization")

    fig, ax = plt.subplots(figsize=figsize)

    for label, ts in series_list:
        history = ts.get_history()
        if history:
            times = [t for t, _ in history]
            values = [v for _, v in history]
            ax.step(times, values, where="post", label=label, linewidth=1.5)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)

    if show:
        plt.show()

    return fig


def plot_utilization_heatmap(
    utilizations: Dict[str, List[float]],
    time_points: List[float],
    title: str = "Resource Utilization",
    figsize: Tuple[int, int] = (12, 6),
    show: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Plot resource utilization heatmap.

    Parameters
    ----------
    utilizations : Dict[str, List[float]]
        Resource name -> utilization values
    time_points : List[float]
        Time points for x-axis
    title : str
        Plot title
    figsize : Tuple[int, int]
        Figure size
    show : bool
        Whether to show plot
    save_path : Optional[str]
        Save path

    Returns
    -------
    Any
        Matplotlib figure
    """
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        raise ImportError("matplotlib and numpy are required for visualization")

    resources = list(utilizations.keys())
    data = np.array([utilizations[r] for r in resources])

    fig, ax = plt.subplots(figsize=figsize)

    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=1)

    ax.set_yticks(range(len(resources)))
    ax.set_yticklabels(resources)

    # Show some time ticks
    n_ticks = min(10, len(time_points))
    tick_indices = np.linspace(0, len(time_points) - 1, n_ticks, dtype=int)
    ax.set_xticks(tick_indices)
    ax.set_xticklabels([f"{time_points[i]:.1f}" for i in tick_indices])

    ax.set_xlabel("Time")
    ax.set_title(title)

    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("Utilization")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)

    if show:
        plt.show()

    return fig
