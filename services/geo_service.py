import math
import json

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in meters.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
        
    R = 6371000  # Radius of earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def point_in_polygon(lat, lng, polygon_coords):
    """
    Ray casting algorithm to determine if a point (lat, lng)
    is inside a polygon represented by a list of [lat, lng] pairs.
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return False

    inside = False
    n = len(polygon_coords)
    p1_lat, p1_lng = polygon_coords[0]

    for i in range(1, n + 1):
        p2_lat, p2_lng = polygon_coords[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                    else:
                        x_inters = p1_lng
                    if p1_lng == p2_lng or lng <= x_inters:
                        inside = not inside
        p1_lat, p1_lng = p2_lat, p2_lng

    return inside


def is_point_in_zone(lat, lng, zone):
    """
    Checks if given lat, lng falls within zone (polygon or circle).
    """
    if zone.boundary_type == 'circle':
        if zone.center_lat is not None and zone.center_lng is not None and zone.radius_meters:
            dist = haversine_distance(lat, lng, zone.center_lat, zone.center_lng)
            return dist <= zone.radius_meters
        return False
    else:
        coords = zone.get_coordinates()
        return point_in_polygon(lat, lng, coords)


def find_current_zone(lat, lng, zones):
    """
    Finds the highest risk zone that contains the point.
    Risk priority: restricted > caution > safe
    """
    matches = []
    for zone in zones:
        if is_point_in_zone(lat, lng, zone):
            matches.append(zone)

    if not matches:
        return None

    # Priority sorting
    priority = {'restricted': 3, 'caution': 2, 'safe': 1}
    matches.sort(key=lambda z: priority.get(z.risk_level, 0), reverse=True)
    return matches[0]


def get_nearest_pois(lat, lng, pois, limit=5):
    """
    Computes distances to all POIs and returns nearest sorted.
    """
    results = []
    for poi in pois:
        dist_m = haversine_distance(lat, lng, poi.lat, poi.lng)
        results.append({
            'poi': poi.to_dict(),
            'distance_meters': round(dist_m),
            'distance_km': round(dist_m / 1000, 2)
        })
    results.sort(key=lambda x: x['distance_meters'])
    return results[:limit]
