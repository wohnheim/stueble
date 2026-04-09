package utils

type ErrorMessage struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func OptionalDereference[T any](ptr *T, fallback T) T {
	if ptr == nil {
		return fallback
	}
	return *ptr
}

func ReverseMap[M ~map[K]V, K, V comparable](m M) map[V]K {
	reversedMap := make(map[V]K, len(m))
	for key, value := range m {
		reversedMap[value] = key
	}
	return reversedMap
}

func CheckMapKey[M ~map[K]V, K, V comparable](m M, k K) bool {
	_, ok := m[k]
	return ok
}

func Bool2Int(b bool) int {
	if b {
		return 1
	} else {
		return 0
	}
}
