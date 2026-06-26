from bot.thresholds import (
    EpochThresholds,
    GovThresholds,
    ParamChangeGroups,
    compute_thresholds,
)

# Representative current-mainnet thresholds for exercising the mapping.
PARAMS = EpochThresholds(
    dvt_motion_no_confidence=0.67,
    dvt_committee_normal=0.67,
    dvt_committee_no_confidence=0.60,
    dvt_update_to_constitution=0.75,
    dvt_hard_fork_initiation=0.60,
    dvt_p_p_network_group=0.67,
    dvt_p_p_economic_group=0.67,
    dvt_p_p_technical_group=0.67,
    dvt_p_p_gov_group=0.75,
    dvt_treasury_withdrawal=0.67,
    pvt_motion_no_confidence=0.51,
    pvt_committee_normal=0.51,
    pvt_committee_no_confidence=0.51,
    pvt_hard_fork_initiation=0.51,
    pvtpp_security_group=0.51,
)
CC_QUORUM = 0.67


class TestComputeThresholds:
    def test_hard_fork_includes_all_three_bodies(self):
        t = compute_thresholds("HardForkInitiation", PARAMS, CC_QUORUM)
        assert t == GovThresholds(drep=0.60, spo=0.51, cc=0.67)

    def test_treasury_withdrawal_omits_spo(self):
        t = compute_thresholds("TreasuryWithdrawals", PARAMS, CC_QUORUM)
        assert t.drep == 0.67
        assert t.spo is None
        assert t.cc == 0.67

    def test_no_confidence_omits_cc(self):
        t = compute_thresholds("NoConfidence", PARAMS, CC_QUORUM)
        assert t.drep == 0.67
        assert t.spo == 0.51
        assert t.cc is None

    def test_new_committee_omits_cc(self):
        t = compute_thresholds("NewCommittee", PARAMS, CC_QUORUM)
        assert t.drep == 0.67
        assert t.spo == 0.51
        assert t.cc is None

    def test_new_constitution_omits_spo(self):
        t = compute_thresholds("NewConstitution", PARAMS, CC_QUORUM)
        assert t.drep == 0.75
        assert t.spo is None
        assert t.cc == 0.67

    def test_info_action_has_note_and_no_bodies(self):
        t = compute_thresholds("InfoAction", PARAMS, CC_QUORUM)
        assert t.drep is None and t.spo is None and t.cc is None
        assert t.note == "none (informational)"

    def test_param_change_non_security_economic(self):
        groups = ParamChangeGroups(economic=True)
        t = compute_thresholds("ParameterChange", PARAMS, CC_QUORUM, param_groups=groups)
        assert t.drep == 0.67
        assert t.spo is None  # not a security-group param
        assert t.cc == 0.67

    def test_param_change_security_includes_spo(self):
        groups = ParamChangeGroups(economic=True, security=True)
        t = compute_thresholds("ParameterChange", PARAMS, CC_QUORUM, param_groups=groups)
        assert t.spo == 0.51

    def test_param_change_governance_group_uses_higher_drep(self):
        groups = ParamChangeGroups(network=True, governance=True)
        t = compute_thresholds("ParameterChange", PARAMS, CC_QUORUM, param_groups=groups)
        # Binding threshold is the highest among touched groups.
        assert t.drep == 0.75

    def test_param_change_without_groups_falls_back(self):
        t = compute_thresholds("ParameterChange", PARAMS, CC_QUORUM, param_groups=None)
        assert t.drep == 0.67
        assert t.spo is None

    def test_unknown_action_type_is_empty(self):
        t = compute_thresholds("SomethingNew", PARAMS, CC_QUORUM)
        assert t.is_empty

    def test_missing_cc_quorum_omits_cc(self):
        t = compute_thresholds("HardForkInitiation", PARAMS, None)
        assert t.cc is None
