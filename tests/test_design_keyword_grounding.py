from agent.design_plan import synthesize_design_plan


def test_clicks_do_not_select_a_cli_terminal_hero():
    plan=synthesize_design_plan({'prompt':'Ceramics shop, editorial asymmetrical composition, repeated clicks working'},domain='ecommerce')
    assert plan.heroArchetype=='editorial_asymmetric'
    assert plan.visualAnchor!='data-terminal'


def test_explicit_design_metadata_wins():
    plan=synthesize_design_plan({'prompt':'Editorial portfolio','heroArchetype':'product_stage'},domain='portfolio')
    assert plan.heroArchetype=='product_stage'
