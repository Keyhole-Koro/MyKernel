# Generic containers

Each module under `generics/` is independently importable through the
compiler's named generic import support. Import every template used by a
specialization, including its container type:

```mln
import { Vec, vec_init, vec_push, vec_pop } from "generics/vec.mln";

i32 main() {
    i32 storage[8];
    Vec<i32> values;
    vec_init<i32>(&values, &storage[0], 8);
    vec_push<i32>(&values, 42);
    i32 value = 0;
    vec_pop<i32>(&values, &value);
    return value;
}
```

| Module | Contents |
| --- | --- |
| `slice.mln` | `Slice<T>` |
| `vec.mln` | `Vec<T>` |
| `arena.mln` | `Arena<T>` |
| `ringbuf.mln` | `RingBuffer<T>` |
| `intrusive_list.mln` | `IntrusiveList<T>` |
| `option.mln` | struct-based `Option<T>` |
| `result.mln` | struct-based `Result<T,E>` |
| `hashmap.mln` | string-keyed `HashMap<T>` |

`Slice<T>`, `Vec<T>`, `Arena<T>`, and `RingBuffer<T>` operate on storage passed
by the caller. `IntrusiveList<T>` is singly linked; each push/pop receives the
address of the payload node's next-link field. `Option<T>` and `Result<T,E>`
are explicit-tag structs until the language gains payload-carrying enums.
`HashMap<T>` maps borrowed NUL-terminated string keys to `T` values using
caller-provided `i32` key-address and value arrays; it has insertion, replacement,
and lookup but not deletion or automatic growth. Its capacity must be a power of two.

Current code generation is reliable for scalar and pointer element types.
Passing aggregate values by value remains outside the container API contract.
