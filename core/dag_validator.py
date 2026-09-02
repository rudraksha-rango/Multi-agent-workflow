import networkx as nx
from core.dag import DAG

class DAGValidator:
    @staticmethod
    def validate(dag: DAG) -> bool:
        graph = nx.DiGraph()
        
        for task_id in dag.nodes:
            graph.add_node(task_id)
            
        for task_id, task in dag.nodes.items():
            for dep_id in task.dependencies:
                if dep_id not in dag.nodes:
                    raise ValueError(f"Dependency {dep_id} for task {task_id} does not exist.")
                graph.add_edge(dep_id, task_id)
                
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("DAG contains cycles!")
            
        return True
