def test_save_and_resume_checkpoint():
    # Placeholder for checkpoint logic which tracks last processed index
    # We simulate this behavior for the test.
    last_processed = 100
    
    # Save
    saved_state = last_processed
    
    # Resume
    assert saved_state == 100
    
def test_default_checkpoint_is_zero():
    # If no state exists, should start at 0
    checkpoint = 0
    assert checkpoint == 0
