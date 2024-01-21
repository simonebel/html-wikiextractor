import bs4


class Node:
    def __init__(
        self,
        next: "Node" = None,
        prev: "Node" = None,
        content: bs4.element.Tag = "",
        id: int = 0,
    ) -> None:
        self.next = next
        self.prev = prev
        self.content = content
        self._id = id

    def __repr__(self) -> str:
        return f"Node({self.content.name if self.content else None}->{self.next})"


class NavigableTree:

    """
    Base interface for navigating a wikipedia article in DFO order while preserving the order of sections
    """

    def __init__(self, root: Node = Node()) -> None:
        self.root = root

    @staticmethod
    def _reach_last(node: Node) -> Node:
        """
        Reach the last node of the tree.
        """
        while node.next != None:
            node = node.next

        return node

    @classmethod
    def build(cls, text: str) -> None:
        """
        Build a navigable tree from an HTML file content.
        """
        html = bs4.BeautifulSoup(text, "html.parser").find("body")
        _id = 0
        visited = [(_id, _id, html)]

        tree = Node()
        while len(visited) > 0:
            current_id, child_of, current_tag = visited.pop(0)
            last = cls._reach_last(tree)

            last.next = Node(prev=last, next=None, content=current_tag, id=_id)

            sections = []
            for tag in current_tag:
                if tag.name == "section":
                    _id += 1
                    sections.append((_id, current_id, tag))

            visited = sections + visited

        return cls(root=tree)

    def __next__(self):
        if self.current.next == None:
            raise StopIteration

        self.current = self.current.next
        return self.current

    def __iter__(self):
        self.current = self.root.next
        return self
