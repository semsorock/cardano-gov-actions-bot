from bot.thresholds import (
    EpochThresholds,
    GovThresholds,
    ParamChangeGroups,
    ThresholdContext,
    build_threshold_context,
    classify_parameters,
    compute_thresholds,
    epoch_thresholds_from_params,
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


def ctx(*, quorum=0.67, dissolved=False, active_size=7, min_size=5) -> ThresholdContext:
    return ThresholdContext(
        params=PARAMS,
        committee_quorum=quorum,
        committee_dissolved=dissolved,
        committee_active_size=active_size,
        committee_min_size=min_size,
    )


class TestComputeThresholds:
    def test_hard_fork_includes_all_three_bodies(self):
        t = compute_thresholds("HardForkInitiation", ctx())
        assert t == GovThresholds(drep=0.60, spo=0.51, cc=0.67)

    def test_treasury_withdrawal_omits_spo(self):
        t = compute_thresholds("TreasuryWithdrawals", ctx())
        assert t.drep == 0.67
        assert t.spo is None
        assert t.cc == 0.67

    def test_no_confidence_omits_cc(self):
        t = compute_thresholds("NoConfidence", ctx())
        assert t.drep == 0.67
        assert t.spo == 0.51
        assert t.cc is None

    def test_new_committee_normal_omits_cc(self):
        t = compute_thresholds("NewCommittee", ctx())
        assert t.drep == 0.67  # dvt_committee_normal
        assert t.spo == 0.51  # pvt_committee_normal
        assert t.cc is None

    def test_new_constitution_omits_spo(self):
        t = compute_thresholds("NewConstitution", ctx())
        assert t.drep == 0.75
        assert t.spo is None
        assert t.cc == 0.67

    def test_info_action_has_note_and_no_bodies(self):
        t = compute_thresholds("InfoAction", ctx())
        assert t.drep is None and t.spo is None and t.cc is None
        assert t.note == "none (informational)"

    def test_param_change_non_security_economic(self):
        groups = ParamChangeGroups(economic=True)
        t = compute_thresholds("ParameterChange", ctx(), param_groups=groups)
        assert t.drep == 0.67
        assert t.spo is None  # not a security-group param
        assert t.cc == 0.67

    def test_param_change_security_includes_spo(self):
        groups = ParamChangeGroups(economic=True, security=True)
        t = compute_thresholds("ParameterChange", ctx(), param_groups=groups)
        assert t.spo == 0.51

    def test_param_change_governance_group_uses_higher_drep(self):
        groups = ParamChangeGroups(network=True, governance=True)
        t = compute_thresholds("ParameterChange", ctx(), param_groups=groups)
        # Binding threshold is the highest among touched groups.
        assert t.drep == 0.75

    def test_param_change_without_groups_shows_no_drep(self):
        # No fabricated economic fallback — DRep number is dropped.
        t = compute_thresholds("ParameterChange", ctx(), param_groups=None)
        assert t.drep is None
        assert t.spo is None
        assert t.cc == 0.67

    def test_unknown_action_type_is_empty(self):
        t = compute_thresholds("SomethingNew", ctx())
        assert t.is_empty

    def test_missing_cc_quorum_omits_cc(self):
        t = compute_thresholds("HardForkInitiation", ctx(quorum=None))
        assert t.cc is None


class TestCommitteeState:
    def test_dissolved_committee_uses_no_confidence_committee_thresholds(self):
        t = compute_thresholds("NewCommittee", ctx(dissolved=True))
        assert t.drep == 0.60  # dvt_committee_no_confidence
        assert t.spo == 0.51  # pvt_committee_no_confidence

    def test_below_min_size_uses_no_confidence_committee_thresholds(self):
        t = compute_thresholds("NewCommittee", ctx(active_size=2, min_size=5))
        assert t.drep == 0.60
        assert t.spo == 0.51

    def test_dissolved_committee_omits_cc_for_cc_voting_actions(self):
        t = compute_thresholds("HardForkInitiation", ctx(dissolved=True))
        assert t.drep == 0.60
        assert t.spo == 0.51
        assert t.cc is None  # no functioning committee to ratify

    def test_below_min_size_omits_cc(self):
        t = compute_thresholds("TreasuryWithdrawals", ctx(active_size=1, min_size=5))
        assert t.cc is None

    def test_context_in_no_confidence_property(self):
        assert ctx(dissolved=True).committee_in_no_confidence is True
        assert ctx(active_size=2, min_size=5).committee_in_no_confidence is True
        assert ctx(active_size=7, min_size=5).committee_in_no_confidence is False


class TestClassifyParameters:
    def test_economic_and_security_for_min_fee_a(self):
        g = classify_parameters({"min_fee_a": 44})
        assert g.economic is True
        assert g.security is True
        assert g.network is False

    def test_network_and_security_for_max_block_size(self):
        g = classify_parameters({"max_block_size": 65536})
        assert g.network is True
        assert g.security is True

    def test_technical_only_for_a0(self):
        g = classify_parameters({"a0": 0.3})
        assert g == ParamChangeGroups(technical=True)

    def test_governance_only_for_gov_action_lifetime(self):
        g = classify_parameters({"gov_action_lifetime": "10"})
        assert g == ParamChangeGroups(governance=True)

    def test_min_fee_ref_script_is_economic_plus_security(self):
        g = classify_parameters({"min_fee_ref_script_cost_per_byte": 15})
        assert g.economic is True
        assert g.security is True
        assert g.technical is False  # reclassified away from technical

    def test_null_values_are_ignored(self):
        g = classify_parameters({"min_fee_a": None, "max_tx_size": 16384})
        assert g.economic is False  # min_fee_a was null
        assert g.network is True

    def test_epoch_and_unknown_fields_ignored(self):
        g = classify_parameters({"epoch": 500, "some_future_param": 1})
        assert g == ParamChangeGroups()

    def test_none_input(self):
        assert classify_parameters(None) == ParamChangeGroups()


class TestEpochThresholdsFromParams:
    def test_reads_all_threshold_fields(self):
        params = {
            "dvt_hard_fork_initiation": 0.6,
            "pvt_hard_fork_initiation": 0.51,
            "dvt_treasury_withdrawal": 0.67,
            "pvt_p_p_security_group": 0.51,
        }
        t = epoch_thresholds_from_params(params)
        assert t.dvt_hard_fork_initiation == 0.6
        assert t.pvt_hard_fork_initiation == 0.51
        assert t.dvt_treasury_withdrawal == 0.67
        assert t.pvtpp_security_group == 0.51

    def test_falls_back_to_deprecated_security_group_name(self):
        params = {"pvtpp_security_group": 0.51}
        t = epoch_thresholds_from_params(params)
        assert t.pvtpp_security_group == 0.51

    def test_missing_fields_are_none(self):
        t = epoch_thresholds_from_params({})
        assert t.dvt_hard_fork_initiation is None
        assert t.pvtpp_security_group is None


class TestBuildThresholdContext:
    def test_parses_committee_min_size_string(self):
        params = {"dvt_treasury_withdrawal": 0.67, "committee_min_size": "5"}
        context = build_threshold_context(
            params,
            committee_quorum=0.67,
            committee_dissolved=False,
            committee_active_size=7,
        )
        assert context.committee_min_size == 5
        assert context.committee_quorum == 0.67
        assert context.params.dvt_treasury_withdrawal == 0.67

    def test_handles_missing_min_size(self):
        context = build_threshold_context(
            {},
            committee_quorum=None,
            committee_dissolved=True,
            committee_active_size=0,
        )
        assert context.committee_min_size is None
        assert context.committee_in_no_confidence is True
