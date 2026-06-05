import matplotlib
matplotlib.use('Agg') # Headless
import matplotlib.pyplot as plt
import seaborn as sns
import os

sns.set_theme(style="darkgrid")

def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def plot_rmse_history(metadata_queryset, output_path: str):
    """Line chart of RMSE over successive training runs. Save as PNG."""
    _ensure_dir(output_path)
    
    records = list(metadata_queryset.order_by('trained_at'))
    if not records:
        return
        
    x = [r.trained_at.strftime('%m-%d %H:%M') for r in records if r.rmse is not None]
    y = [r.rmse for r in records if r.rmse is not None]
    
    if not x:
        return
        
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=x, y=y, marker='o')
    plt.title('RMSE History over Training Runs')
    plt.xlabel('Training Time')
    plt.ylabel('RMSE')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_precision_recall(precision_vals: list, recall_vals: list, k_vals: list, output_path: str):
    """Precision and Recall vs K line chart. Save as PNG."""
    _ensure_dir(output_path)
    
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=k_vals, y=precision_vals, marker='o', label='Precision')
    sns.lineplot(x=k_vals, y=recall_vals, marker='s', label='Recall')
    plt.title('Precision and Recall vs K')
    plt.xlabel('K (Number of Recommendations)')
    plt.ylabel('Score')
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_recommendation_score_distribution(scores: list, output_path: str):
    """Histogram of hybrid scores across all recommendations. Save as PNG."""
    _ensure_dir(output_path)
    
    if not scores:
        return
        
    plt.figure(figsize=(10, 6))
    sns.histplot(scores, bins=30, kde=True, color='skyblue')
    plt.title('Distribution of Hybrid Recommendation Scores')
    plt.xlabel('Hybrid Score')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def plot_coverage_diversity(coverage: float, diversity: float, output_path: str):
    """Simple bar chart comparing coverage and diversity. Save as PNG."""
    _ensure_dir(output_path)
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=['Coverage', 'Diversity'], y=[coverage, diversity], palette='viridis')
    plt.title('Catalog Coverage and Recommendation Diversity')
    plt.ylabel('Score (0.0 to 1.0)')
    plt.ylim(0, 1.0)
    
    # Add value labels on top of bars
    for i, v in enumerate([coverage, diversity]):
        plt.text(i, v + 0.02, f'{v:.3f}', ha='center')
        
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
