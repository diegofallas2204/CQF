from typing import List

class SortingAlgorithms:
    """
    Implementación de algoritmos de ordenamiento para diferentes criterios.
    """

    @staticmethod
    def quick_sort(arr: List, key_func=None, reverse=False) -> List:
        """
        Quick Sort con función de clave personalizable.
        Complejidad: O(n log n) promedio, O(n²) peor caso
        """
        if len(arr) <= 1:
            return arr.copy()

        if key_func is None:
            key_func = lambda x: x

        pivot_idx = len(arr) // 2
        pivot = arr[pivot_idx]
        pivot_key = key_func(pivot)

        left = []
        right = []
        equal = []

        for item in arr:
            item_key = key_func(item)
            if item_key < pivot_key:
                left.append(item)
            elif item_key > pivot_key:
                right.append(item)
            else:
                equal.append(item)

        sorted_left = SortingAlgorithms.quick_sort(left, key_func, reverse)
        sorted_right = SortingAlgorithms.quick_sort(right, key_func, reverse)

        if reverse:
            return sorted_right + equal + sorted_left
        else:
            return sorted_left + equal + sorted_right

    @staticmethod
    def merge_sort(arr: List, key_func=None, reverse=False) -> List:
        """
        Merge Sort - más estable que Quick Sort.
        Complejidad: O(n log n) garantizado
        """
        if len(arr) <= 1:
            return arr.copy()

        if key_func is None:
            key_func = lambda x: x

        mid = len(arr) // 2
        left = SortingAlgorithms.merge_sort(arr[:mid], key_func, reverse)
        right = SortingAlgorithms.merge_sort(arr[mid:], key_func, reverse)

        return SortingAlgorithms._merge(left, right, key_func, reverse)

    @staticmethod
    def _merge(left: List, right: List, key_func, reverse: bool) -> List:
        """Función auxiliar para merge sort"""
        result = []
        i = j = 0

        while i < len(left) and j < len(right):
            left_key = key_func(left[i])
            right_key = key_func(right[j])

            condition = left_key <= right_key if not reverse else left_key >= right_key

            if condition:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1

        result.extend(left[i:])
        result.extend(right[j:])
        return result

