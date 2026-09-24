"""
Git graph visualization using Plotly.
Renders commits, branches, and HEAD pointer.
"""

import plotly.graph_objects as go
from git_simulator.state import GitState, Commit
from typing import Dict, Tuple, List


def render_git_graph(state: GitState) -> go.Figure:
    """
    Render interactive commit graph.
    
    Args:
        state: GitState snapshot
    
    Returns:
        Plotly figure object
    """
    fig = go.Figure()
    
    if not state.commits:
        # No commits yet
        fig.add_annotation(
            text="No commits yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title="Git Commit History",
            height=400,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='rgba(240,240,240,0.5)',
            margin=dict(b=20, l=5, r=5, t=40),
        )
        return fig
    
    # Calculate positions for commits
    positions = _calculate_positions(state.commits, state)
    
    # Draw parent-child relationships (edges)
    for sha, commit in state.commits.items():
        if commit.parents:
            x_child, y_child = positions.get(sha, (0, 0))
            
            for parent_sha in commit.parents:
                if parent_sha in positions:
                    x_parent, y_parent = positions[parent_sha]
                    
                    # Draw line from parent to child
                    fig.add_trace(go.Scatter(
                        x=[x_parent, x_child],
                        y=[y_parent, y_child],
                        mode='lines',
                        line=dict(color='lightgray', width=2),
                        hoverinfo='none',
                        showlegend=False,
                        name=''
                    ))
    
    # Draw commits
    for sha, commit in state.commits.items():
        x, y = positions.get(sha, (0, 0))
        
        # Determine if this is the current commit
        current_sha = state.get_head_commit_sha()
        is_current = (sha == current_sha)
        
        # Color based on status
        if is_current:
            color = "gold"
            size = 25
            line_width = 3
            line_color = "orange"
        else:
            color = "lightblue"
            size = 20
            line_width = 2
            line_color = "navy"
        
        # Create hover text
        hover_text = f"""
        <b>{commit.short_sha}</b><br>
        <b>{commit.message}</b><br>
        <br>
        Author: {commit.author}<br>
        Parents: {', '.join(p[:7] for p in commit.parents) if commit.parents else 'root'}
        """
        
        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode='markers',
            marker=dict(
                size=size,
                color=color,
                line=dict(color=line_color, width=line_width)
            ),
            text=[commit.short_sha],
            textposition='middle center',
            textfont=dict(size=10, color='black', family='monospace'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False,
            name=''
        ))
    
    # Add branch labels
    for branch_name, branch_ptr in state.branches.items():
        if branch_ptr.target_sha and branch_ptr.target_sha in positions:
            x, y = positions[branch_ptr.target_sha]
            
            # Position label slightly below commit
            label_y = y - 0.6
            
            fig.add_annotation(
                x=x,
                y=label_y,
                text=f"<b>{branch_name}</b>",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="green",
                font=dict(size=11, color="green", family='monospace'),
                bgcolor="rgba(144, 238, 144, 0.3)",
                bordercolor="green",
                borderwidth=1,
                borderpad=4
            )
    
    # Add remote-tracking labels. These are intentionally styled differently
    # from local branches so learners can see local refs vs remote refs.
    for remote_name, remote_branches in state.remotes.items():
        for branch_name, branch_ptr in remote_branches.items():
            if branch_ptr.target_sha and branch_ptr.target_sha in positions:
                x, y = positions[branch_ptr.target_sha]
                fig.add_annotation(
                    x=x + 0.35,
                    y=y - 0.05,
                    text=f"<b>{remote_name}/{branch_name}</b>",
                    showarrow=False,
                    font=dict(size=9, color="purple", family="monospace"),
                    bgcolor="rgba(220, 200, 255, 0.35)",
                    bordercolor="purple",
                    borderwidth=1,
                    borderpad=3,
                )

    # Add HEAD label
    if not state.head_is_detached:
        if state.head in state.branches:
            current_sha = state.branches[state.head].target_sha
        else:
            current_sha = state.get_head_commit_sha()
    else:
        current_sha = state.head
    
    if current_sha and current_sha in positions:
        x, y = positions[current_sha]
        
        label_y = y + 0.6
        
        fig.add_annotation(
            x=x,
            y=label_y,
            text="<b>HEAD</b>" + (f"<br><i>({state.head[:7]})</i>" if state.head_is_detached else ""),
            showarrow=True,
            arrowhead=2,
            arrowside='down',
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="red",
            font=dict(size=11, color="red", family='monospace'),
            bgcolor="rgba(255, 200, 200, 0.3)",
            bordercolor="red",
            borderwidth=1,
            borderpad=4
        )
    
    # Update layout
    fig.update_layout(
        title="Git Commit History",
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        showlegend=False,
        height=500,
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min(positions.values(), key=lambda p: p[0])[0] - 1 if positions else -1,
                   max(positions.values(), key=lambda p: p[0])[0] + 1 if positions else 1]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        plot_bgcolor='rgba(240,240,240,0.5)'
    )
    
    return fig



def render_git_animation(states: List[GitState], speed: float = 1.0) -> go.Figure:
    """Render command-history states as a playable Plotly animation."""
    if not states:
        return render_git_graph(GitState())

    base = render_git_graph(states[-1])
    frames = []
    for index, state in enumerate(states):
        frame_fig = render_git_graph(state)
        frames.append(
            go.Frame(
                data=list(frame_fig.data),
                layout=frame_fig.layout,
                name=str(index),
            )
        )

    duration = max(150, int(700 / max(speed, 0.1)))
    base.frames = frames
    base.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                x=0.02,
                y=1.12,
                xanchor="left",
                yanchor="top",
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[
                            None,
                            {
                                "frame": {"duration": duration, "redraw": True},
                                "transition": {"duration": max(80, duration // 2)},
                                "fromcurrent": True,
                            },
                        ],
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[
                            [None],
                            {
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                            },
                        ],
                    ),
                ],
            )
        ],
        sliders=[
            dict(
                active=len(states) - 1,
                x=0.02,
                y=-0.08,
                xanchor="left",
                yanchor="top",
                currentvalue={"prefix": "Command step: "},
                steps=[
                    dict(
                        label=str(i + 1),
                        method="animate",
                        args=[
                            [str(i)],
                            {
                                "frame": {"duration": 0, "redraw": True},
                                "transition": {"duration": 0},
                            },
                        ],
                    )
                    for i in range(len(states))
                ],
            )
        ],
    )
    return base

def _calculate_positions(commits: dict, state: GitState) -> Dict[str, Tuple[float, float]]:
    """
    Calculate x, y positions for commits in a DAG layout.
    
    Uses a simple topological sort approach:
    - Y position based on depth from leaf commits
    - X position based on branch
    
    Args:
        commits: Dictionary of commits
        state: GitState for reference
    
    Returns:
        Dictionary mapping commit SHA to (x, y) positions
    """
    if not commits:
        return {}
    
    positions = {}
    
    # Build reverse graph (parents -> children)
    children_map = {}
    depth_map = {}
    
    for sha, commit in commits.items():
        if sha not in children_map:
            children_map[sha] = []
        for parent_sha in commit.parents:
            if parent_sha not in children_map:
                children_map[parent_sha] = []
            children_map[parent_sha].append(sha)
    
    # Calculate depth from leaves
    def calculate_depth(sha: str) -> int:
        if sha in depth_map:
            return depth_map[sha]
        
        commit = commits.get(sha)
        if not commit or not commit.parents:
            depth_map[sha] = 0
            return 0
        
        max_parent_depth = max(calculate_depth(p) for p in commit.parents)
        depth_map[sha] = max_parent_depth + 1
        return depth_map[sha]
    
    for sha in commits:
        calculate_depth(sha)
    
    # Calculate maximum depth
    max_depth = max(depth_map.values()) if depth_map else 0
    
    # Assign positions
    branch_positions = {}  # branch_name -> x_offset
    x_offset = 0
    
    for branch_name in sorted(state.branches.keys()):
        branch_positions[branch_name] = x_offset
        x_offset += 2
    
    # Assign x, y coordinates
    for sha, commit in commits.items():
        y = (max_depth - depth_map.get(sha, 0)) * 1.5
        
        # Find which branch this commit belongs to
        x = 0
        for branch_name, branch_ptr in state.branches.items():
            if branch_ptr.target_sha == sha:
                x = branch_positions.get(branch_name, 0)
                break
        
        if x == 0 and not any(branch_ptr.target_sha == sha for branch_ptr in state.branches.values()):
            # Commit not pointed to by any branch, place in middle
            x = x_offset / 2
        
        positions[sha] = (x, y)
    
    return positions
