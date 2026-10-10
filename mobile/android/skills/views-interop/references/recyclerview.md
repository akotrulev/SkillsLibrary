# RecyclerView — ListAdapter and stable ids

## `RecyclerView` — `ListAdapter` and stable ids

```kotlin
class OrdersAdapter(private val onClick: (OrderId) -> Unit) :
    ListAdapter<OrderRow, OrdersAdapter.Holder>(Diff) {

    init {
        setHasStableIds(true)
    }

    override fun getItemId(position: Int): Long = getItem(position).id.stableLong()

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): Holder =
        Holder(ItemOrderBinding.inflate(LayoutInflater.from(parent.context), parent, false), onClick)

    override fun onBindViewHolder(holder: Holder, position: Int) = holder.bind(getItem(position))

    class Holder(private val views: ItemOrderBinding, private val onClick: (OrderId) -> Unit) :
        RecyclerView.ViewHolder(views.root) {
        fun bind(row: OrderRow) {
            views.title.text = row.title
            views.root.setOnClickListener { onClick(row.id) }
        }
    }

    private object Diff : DiffUtil.ItemCallback<OrderRow>() {
        override fun areItemsTheSame(old: OrderRow, new: OrderRow) = old.id == new.id
        override fun areContentsTheSame(old: OrderRow, new: OrderRow) = old == new
    }
}
```

- **`ListAdapter` + `DiffUtil`** with `areItemsTheSame` on the **domain id**, never the position. `notifyDataSetChanged()` is a finding (kills animations and scroll position).
- `onBindViewHolder` does no work beyond assigning — no formatting, I/O or image decode; an image library (Coil's `load`) cancels with the view.
- Listeners are set once per holder where the data allows; a click lambda captures the **id**, not the stale `position`.
- The adapter holds no `Context` of an Activity and no ViewModel; it takes lambdas.
- Empty / loading / failed are a **sibling view** switched by `render` (a `ViewFlipper`-style container or `isVisible` flags driven by one `when (state)`), scoped to the list body — the search bar and toolbar stay.
