import numpy as np


def make_offset_polygon(corners_in, offsets):
    assert len(corners_in) == len(offsets)

    num_sides = len(corners_in)
    offset_polygon = []
    for i in range(num_sides):
        prev_i = (i + num_sides - 1) % num_sides
        next_i = (i + 1) % num_sides

        prev_point = np.array(corners_in[prev_i])
        current_point = np.array(corners_in[i])
        next_point = np.array(corners_in[next_i])

        vec1 = current_point - prev_point
        vec2 = next_point - current_point
        vec1_hat = vec1 / np.linalg.norm(vec1)
        vec2_hat = vec2 / np.linalg.norm(vec2)

        rot_mat = np.array([[0, -1], [1, 0]])
        vec1_hat_perp = rot_mat @ vec1_hat
        vec2_hat_perp = rot_mat @ vec2_hat

        p1 = current_point + vec1_hat_perp * offsets[prev_i]
        p2 = current_point + vec2_hat_perp * offsets[i]
        t2 = ((p2[1] - p1[1]) * vec1_hat[0] - (p2[0] - p1[0]) * vec1_hat[1]) / (
            vec2_hat[0] * vec1_hat[1] - vec2_hat[1] * vec1_hat[0]
        )
        offset_point = p2 + t2 * vec2_hat

        offset_polygon.append(offset_point)
    return offset_polygon


def distance_from_line(point, line_start, line_end, clip=False):
    point = np.array(point)
    line_start = np.array(line_start)
    line_end = np.array(line_end)

    line_vec = line_end - line_start
    line_length = np.linalg.norm(line_vec)
    line_vec_hat = line_vec / line_length

    point_vec = point - line_start
    point_vec_proj_length = np.dot(point_vec, line_vec_hat)

    if clip and point_vec_proj_length < 0:
        return np.linalg.norm(point_vec)
    elif clip and point_vec_proj_length > line_length:
        return np.linalg.norm(point - line_end)
    else:
        rot_mat = np.array([[0, -1], [1, 0]])
        line_vec_hat_perp = rot_mat @ line_vec_hat
        return np.abs(np.dot(point_vec, line_vec_hat_perp))


def offset_at_centre(line_start, line_end, offset):
    line_start = np.array(line_start)
    line_end = np.array(line_end)

    line_vec = line_end - line_start
    line_length = np.linalg.norm(line_vec)
    line_vec_hat = line_vec / line_length

    line_centre = line_start + line_vec * 0.5

    rot_mat = np.array([[0, -1], [1, 0]])
    line_vec_hat_perp = rot_mat @ line_vec_hat

    return line_centre + np.abs(offset) * line_vec_hat_perp


def area_quadrilateral(corners_in):
    vertices = np.array(corners_in)

    vec1 = vertices[2] - vertices[0]
    vec2 = vertices[3] - vertices[1]

    return np.linalg.norm(np.cross(vec1, vec2)) / 2


if __name__ == "__main__":
    c = ((0, 0), (0, 1), (1, 1), (1, 0))
    o = (1, 1, 0, 1)

    offset_c = make_offset_polygon(c, o)
    distance_from_line((0.5, 0.5), (0, 0), (0, 1))
    area_quadrilateral(c)
