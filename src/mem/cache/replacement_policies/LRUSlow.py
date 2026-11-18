# Team 9


from m5.objects.ReplacementPolicies import BaseReplacementPolicy
from m5.params import Param
from m5.proxy import Parent


class LRUSlow(BaseReplacementPolicy):
    type = "LRUSlow"
    cxx_class = "gem5::replacement_policy::LRUSlow"
    cxx_header = "mem/cache/replacement_policies/lru_slow_rp.hh"

    num_ways = Param.Unsigned(
        Parent.assoc, "Number of ways sharing one recency stack"
    )
