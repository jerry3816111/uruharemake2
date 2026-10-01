from copy import deepcopy

import ssl

import p3_b52_metadata_only_source_freeze_v4 as v4


def test_v4_changes_only_verified_tls_transport_and_keeps_v3_valid():
    report = v4.validate_contract()
    assert report == {"valid": True, "errors": [], "v3_contract_valid": True}


def test_ssl_context_requires_certificate_and_hostname_verification():
    context = v4.build_verified_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_insecure_or_non_tls_transport_change_is_rejected():
    config = v4.load_config()
    insecure = deepcopy(config)
    insecure["tls_transport"]["certificate_verification_enabled"] = False
    insecure["tls_transport"]["http_endpoint_change"] = True
    report = v4.validate_contract(insecure)
    assert report["valid"] is False
    assert "certificate_verification_disabled" in report["errors"]
    assert "non_tls_transport_change_detected" in report["errors"]


def test_v4_implementation_is_frozen_before_network_access():
    report = v4.validate_implementation_freeze()
    assert report == {
        "valid": True,
        "v3_response_bytes_retained": 0,
        "v4_atom_retrieval_count_at_freeze": 0,
        "selected_id_postcheck_count_at_freeze": 0,
    }
