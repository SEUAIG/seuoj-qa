from code_runner import code_runner


def test_example():
    code = """
#include <iostream>
#include <vector>

std::vector<int> bubbleSort(std::vector<int>& arr) {
    int n = arr.size();
    if (n == 0 || n == 1) {
        return arr;
    }
    
    for (int i = 0; i < n - 1; ++i) {
        bool swapped = false;
        for (int j = 0; j < n - i - 1; ++j) {
            if (arr[j] > arr[j + 1]) {
                std::swap(arr[j], arr[j + 1]);
                swapped = true;
            }
        }
        if (!swapped) {
            break;
        }
    }
    return arr;
}

void printArray(const std::vector<int>& arr) {
    for (int num : arr) {
        std::cout << num << " ";
    }
    std::cout << std::endl;
}

int main() {
    // 测试用例
    std::vector<std::vector<int>> testCases = {
        {},                          // 空数组
        {1},                         // 单元素数组
        {5, 3, 8, 4, 2},            // 普通数组
        {1, 2, 3, 4, 5},            // 已排序数组
        {5, 4, 3, 2, 1},            // 逆序数组
        {2, 1},                     // 两个元素，逆序
        {1, 2},                     // 两个元素，已排序
        {3, 3, 2, 1, 1, 2, 3},      // 包含重复元素
        {10, -1, 2, 0, -5, 3}       // 包含负数和零
    };

    for (const auto& testCase : testCases) {
        std::vector<int> arr = testCase;
        std::cout << "Original array: ";
        printArray(arr);
        std::vector<int> sortedArr = bubbleSort(arr);
        std::cout << "Sorted array: ";
        printArray(sortedArr);
    }

    return 0;
}
"""

    result = code_runner(
        code=code,
        stdin="10 20\n",
        language="Cpp17"
    )

    print(result)


if __name__ == "__main__":
    test_example()