// Original C++17 raster operations. The public ABI uses interleaved RGB bytes.
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>

#ifdef _WIN32
#define PP_API extern "C" __declspec(dllexport)
#else
#define PP_API extern "C" __attribute__((visibility("default")))
#endif

PP_API int pp_version() noexcept { return 1; }

// Returns 0 on success, -1 for invalid input, -2 for allocation failure.
// Exceptions never cross the C boundary. The Python caller works on a copy.
PP_API int pp_flood_fill(std::uint8_t* pixels, std::size_t length,
                        int width, int height, int x, int y,
                        std::uint8_t red, std::uint8_t green, std::uint8_t blue) noexcept {
    if (!pixels || width <= 0 || height <= 0 || x < 0 || y < 0 || x >= width || y >= height)
        return -1;
    const auto w = static_cast<std::size_t>(width);
    const auto h = static_cast<std::size_t>(height);
    if (w > std::numeric_limits<std::size_t>::max() / h / 3 || length != w * h * 3)
        return -1;
    const auto start = static_cast<std::size_t>(y) * w + static_cast<std::size_t>(x);
    const std::uint8_t r = pixels[start * 3], g = pixels[start * 3 + 1], b = pixels[start * 3 + 2];
    if (r == red && g == green && b == blue) return 0;
    auto matches = [&](std::size_t i) {
        return pixels[i * 3] == r && pixels[i * 3 + 1] == g && pixels[i * 3 + 2] == b;
    };
    auto recolor = [&](std::size_t i) {
        pixels[i * 3] = red; pixels[i * 3 + 1] = green; pixels[i * 3 + 2] = blue;
    };
    try {
        std::vector<std::size_t> pending;
        pending.push_back(start);
        recolor(start);
        while (!pending.empty()) {
            const auto index = pending.back();
            pending.pop_back();
            const auto col = index % w;
            auto visit = [&](std::size_t neighbor) {
                if (matches(neighbor)) {
                    pending.push_back(neighbor);
                    recolor(neighbor);
                }
            };
            if (col > 0) visit(index - 1);
            if (col + 1 < w) visit(index + 1);
            if (index >= w) visit(index - w);
            if (index + w < w * h) visit(index + w);
        }
        return 0;
    } catch (...) {
        return -2;
    }
}
