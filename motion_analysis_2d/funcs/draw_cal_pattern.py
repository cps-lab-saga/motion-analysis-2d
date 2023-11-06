from defs import QtCore, QtWidgets, QtGui


def make_pattern_pixmap(
    screen, cols, rows, square_size, radius_rate=5, pattern="Checkerboard"
):
    width_mm = screen.physicalSize().width()
    height_mm = screen.physicalSize().height()

    width_px = screen.size().width()
    height_px = screen.size().height()

    x_size = square_size / width_mm * width_px
    y_size = square_size / height_mm * height_px

    pixmap = QtGui.QPixmap(width_px, height_px)

    if pattern == "Checkerboard":
        draw_checkerboard_pattern(
            pixmap, cols, rows, x_size, y_size, width_px, height_px
        )
    elif pattern == "Circles":
        draw_circles_pattern(
            pixmap, cols, rows, radius_rate, x_size, y_size, width_px, height_px
        )
    elif pattern == "Asymmetric Circles":
        draw_acircles_pattern(
            pixmap, cols, rows, radius_rate, x_size, y_size, width_px, height_px
        )

    return pixmap


def draw_checkerboard_pattern(
    paint_device, cols, rows, x_size, y_size, page_width, page_height
):
    painter = QtGui.QPainter(paint_device)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setRenderHints(QtGui.QPainter.Antialiasing)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))

    painter.drawRect(0, 0, page_width, page_height)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("black")))
    x_spacing = (page_width - cols * x_size) / 2
    y_spacing = (page_height - rows * y_size) / 2
    for x in range(0, cols):
        for y in range(0, rows):
            if x % 2 == y % 2:
                painter.drawRect(
                    round(x * x_size + x_spacing),
                    round(y * y_size + y_spacing),
                    round(x_size),
                    round(y_size),
                )

    painter.end()


def draw_circles_pattern(
    paint_device, cols, rows, radius_rate, x_size, y_size, page_width, page_height
):
    painter = QtGui.QPainter(paint_device)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setRenderHints(QtGui.QPainter.Antialiasing)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))

    painter.drawRect(0, 0, page_width, page_height)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("black")))

    r_x = x_size / radius_rate
    r_y = y_size / radius_rate

    pattern_width = ((cols - 1) * x_size) + (2 * r_x)
    pattern_height = ((rows - 1) * y_size) + (2 * r_y)

    x_spacing = (page_width - pattern_width) / 2
    y_spacing = (page_height - pattern_height) / 2

    for x in range(0, cols):
        for y in range(0, rows):
            painter.drawEllipse(
                round((x * x_size) + x_spacing),
                round((y * y_size) + y_spacing),
                round(r_x),
                round(r_y),
            )

    painter.end()


def draw_acircles_pattern(
    paint_device, cols, rows, radius_rate, x_size, y_size, page_width, page_height
):
    painter = QtGui.QPainter(paint_device)
    painter.setPen(QtCore.Qt.NoPen)
    painter.setRenderHints(QtGui.QPainter.Antialiasing)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("white")))

    painter.drawRect(0, 0, page_width, page_height)

    painter.setBrush(QtGui.QBrush(QtGui.QColor("black")))

    r_x = x_size / radius_rate
    r_y = y_size / radius_rate

    pattern_width = ((cols - 1) * 2 * x_size) + (2 * r_x)
    pattern_height = ((rows - 1) * y_size) + (2 * r_y)

    x_spacing = (page_width - pattern_width) / 2
    y_spacing = (page_height - pattern_height) / 2

    for x in range(0, cols):
        for y in range(0, rows):
            painter.drawEllipse(
                round((2 * x * x_size) + (y % 2) * x_size + x_spacing),
                round((y * y_size) + y_spacing),
                round(r_x),
                round(r_y),
            )

    painter.end()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    screens = app.screens()
    my_screen = screens[0]

    splash = QtWidgets.QSplashScreen()
    pattern_pixmap = make_pattern_pixmap(
        my_screen, 20, 20, 10, radius_rate=2, pattern="Checkerboard"
    )
    splash.setPixmap(pattern_pixmap)

    splash.show()
    splash.windowHandle().setScreen(my_screen)
    splash.showFullScreen()

    app.exec()
