from flask import Flask, render_template, request, jsonify
from geopy.distance import great_circle
from geopy.geocoders import Nominatim
import os

import matplotlib
matplotlib.use('Agg')  # Fixes matplotlib GUI warnings
import matplotlib.pyplot as plt
import networkx as nx
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

app = Flask(__name__)

# Fetch city coordinates
def fetch_coordinates(cities):
    geolocator = Nominatim(user_agent="city_locator")
    location_dict = {}
    for city in cities:
        try:
            location = geolocator.geocode(city, timeout=10)  # Increase timeout
            if location:
                location_dict[city] = (location.latitude, location.longitude)
            else:
                print(f"Could not find location for city: {city}")
                raise ValueError(f"Invalid city: {city}")
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"Geocoding error for city '{city}': {e}")
            raise ValueError(f"Geocoding service is unavailable for city: {city}")
    return location_dict

# Graph Implementation (Kruskal's)
class Graph:
    def __init__(self, vertices): 
        self.V = vertices
        self.graph = []

    def addEdge(self, u, v, w):
        self.graph.append([u, v, w])

    def find(self, parent, i):
        if parent[i] == i:
            return i
        return self.find(parent, parent[i])

    def union(self, parent, rank, x, y):
        xroot = self.find(parent, x)
        yroot = self.find(parent, y)
        if rank[xroot] < rank[yroot]:
            parent[xroot] = yroot
        elif rank[xroot] > rank[yroot]:
            parent[yroot] = xroot
        else:
            parent[yroot] = xroot
            rank[xroot] += 1

    def KruskalMST(self):
        result = []
        self.graph = sorted(self.graph, key=lambda item: item[2])
        parent = []
        rank = []

        for node in range(self.V):
            parent.append(node)
            rank.append(0)

        e = 0
        i = 0
        while e < self.V - 1:
            u, v, w = self.graph[i]
            i += 1
            x = self.find(parent, u)
            y = self.find(parent, v)
            if x != y:
                result.append([u, v, w])
                self.union(parent, rank, x, y)
                e += 1
        return result

# Visualization
def visualize_graph(cities, location_dict, edges, filename, title):
    try:
        # Create the graph and add edges
        G = nx.Graph()
        positions = {i: location_dict[city] for i, city in enumerate(cities)}

        for edge in edges:
            u, v, w = edge
            G.add_edge(u, v, weight=w)

        # Use spring layout for uniform edge lengths
        pos = nx.spring_layout(G, scale=2, seed=42)  # `scale` controls overall spacing

        # Adjust figure size dynamically based on the number of nodes
        num_nodes = len(cities)
        if num_nodes <= 3:
            figsize = (5, 5)  # Small graph
        elif num_nodes <= 6:
            figsize = (8, 8)  # Medium graph
        else:
            figsize = (12, 12)  # Large graph

        # Plot the graph
        plt.figure(figsize=figsize)
        nx.draw(G, pos, with_labels=True, labels={i: cities[i] for i in range(len(cities))},
                node_color="skyblue", node_size=3000, font_size=10, font_weight="bold")

        # Add edge labels with weights
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels={(u, v): f"{w} km" for u, v, w in edges})

        plt.title(title, fontsize=15)
        plt.tight_layout()  # Adjust padding
        plt.savefig(filename)
        plt.close()

    except Exception as e:
        print(f"Error visualizing graph: {e}")



# Flask Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    try:
        cities = request.form.get("cities", "").split(",")
        cities = [city.strip() for city in cities if city.strip()]

        if not cities:
            return render_template("submit.html", error="No cities provided.")

        location_dict = fetch_coordinates(cities)

        g = Graph(len(cities))
        for i, city1 in enumerate(cities):
            for j, city2 in enumerate(cities):
                if i < j:
                    dist = int(great_circle(location_dict[city1], location_dict[city2]).km)
                    g.addEdge(i, j, dist)

        mst_result = g.KruskalMST()

        os.makedirs("static", exist_ok=True)
        graph_before_path = "static/Graph_Before_MST.png"
        graph_after_path = "static/Graph_After_MST.png"
        visualize_graph(cities, location_dict, g.graph, graph_before_path, "Graph Before MST")
        visualize_graph(cities, location_dict, mst_result, graph_after_path, "Graph After MST")

        mst_edges = [{"from": cities[u], "to": cities[v], "weight": w} for u, v, w in mst_result]

        return render_template(
            "submit.html",
            mst_edges=mst_edges,
            before_mst_image="/" + graph_before_path,
            after_mst_image="/" + graph_after_path,
        )
    except Exception as e:
        print(f"Error in /submit: {e}")
        return render_template("submit.html", error=str(e), mst_edges=[])




@app.route("/generate_mst", methods=["POST"])
def generate_mst():
    try:
        cities = request.json.get("cities", [])
        if not cities:
            return jsonify({"error": "No cities provided."}), 400

        # Fetch coordinates
        location_dict = fetch_coordinates(cities)

        # Build the graph
        g = Graph(len(cities))
        for i, city1 in enumerate(cities):
            for j, city2 in enumerate(cities):
                if i < j:
                    dist = int(great_circle(location_dict[city1], location_dict[city2]).km)
                    g.addEdge(i, j, dist)

        # Generate MST
        mst_result = g.KruskalMST()

        # Save the graphs
        os.makedirs("static", exist_ok=True)
        graph_before_path = "static/Graph_Before_MST.png"
        graph_after_path = "static/Graph_After_MST.png"
        visualize_graph(cities, location_dict, g.graph, graph_before_path, "Graph Before MST")
        visualize_graph(cities, location_dict, mst_result, graph_after_path, "Graph After MST")

        # Prepare response data
        mst_edges = [{"from": cities[u], "to": cities[v], "weight": w} for u, v, w in mst_result]
        return jsonify({
            "mst_edges": mst_edges,
            "before_mst_image": "/" + graph_before_path,
            "after_mst_image": "/" + graph_after_path
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


    
if __name__ == "__main__":
    app.run(debug=True)

