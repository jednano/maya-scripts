#=================================================
# functions
#=================================================

def nearest_point_on_line(line, point):
	delta = line[1] - line[0]
	return line[0] + (delta * (point - line[0])) * delta / (delta * delta)