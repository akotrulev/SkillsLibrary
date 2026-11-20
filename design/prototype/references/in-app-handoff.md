# In-app hand-off

The brief handed to the stack agent carries:

- the prototype file and the variants to build (all of them, or the shortlist);
- the host: the existing route or screen, switched by a `?variant=` parameter (or the platform's equivalent: a launch argument, a debug menu). A new throwaway route, named with `prototype` in its path, only when no existing page can host it;
- the data fetching kept above the switch, so only the rendered subtree changes; mutations pointed at stubs;
- the switcher kept out of production builds;
- the verdict so far, and the rule for afterwards: the winner is rewritten to the house rules when folded in, and the losing variants and the switcher are removed.

Done when the brief holds each of the five items above.
