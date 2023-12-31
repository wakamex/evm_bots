"""Testing adding & removing liquidity"""

import unittest

from fixedpointmath import FixedPoint

import elfpy.time as time
from elfpy.agents.agent import Agent
from elfpy.agents.policies import NoActionPolicy
from elfpy.markets.hyperdrive import HyperdriveMarket, HyperdriveMarketState, HyperdrivePricingModel, hyperdrive_actions


class TestAddLiquidity(unittest.TestCase):
    """Test adding liquidity to hyperdrive"""

    APPROX_EQ: FixedPoint = FixedPoint(1e-1)

    contribution = FixedPoint("500_000_000.0")
    target_apr = FixedPoint("0.05")
    alice: Agent
    bob: Agent
    celine: Agent
    hyperdrive: HyperdriveMarket
    block_time: time.BlockTime

    def setUp(self):
        self.alice = Agent(wallet_address=0, policy=NoActionPolicy(budget=self.contribution))
        self.bob = Agent(wallet_address=1, policy=NoActionPolicy(budget=self.contribution))
        self.celine = Agent(wallet_address=1, policy=NoActionPolicy(budget=self.contribution))
        self.block_time = time.BlockTime()

        pricing_model = HyperdrivePricingModel()
        market_state = HyperdriveMarketState()

        self.hyperdrive = HyperdriveMarket(
            pricing_model=pricing_model,
            market_state=market_state,
            block_time=self.block_time,
            position_duration=time.StretchedTime(
                days=FixedPoint("365.0"),
                time_stretch=pricing_model.calc_time_stretch(self.target_apr),
                normalizing_constant=FixedPoint("365.0"),
            ),
        )
        _, wallet_deltas = self.hyperdrive.initialize(self.contribution, FixedPoint("0.05"))
        self.alice.wallet.update(wallet_deltas)

    def test_add_liquidity_failure_zero_amount(self):
        """Test adding zero liquidity fails"""
        with self.assertRaises(AssertionError):
            self.hyperdrive.add_liquidity(self.bob.wallet, FixedPoint(0))

    def test_add_liquidity_identical_lp_shares(self):
        """Test adding liquidity equal to the total liquidity of the pool creates the same number of
        shares that are in the pool."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, delta=self.APPROX_EQ)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * FixedPoint("2.0"))

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, delta=self.APPROX_EQ)

    def test_add_liquidity_with_long_immediately(self):
        """Test adding liquidity when there is a long open.  LP should still get the same number of
        shares as if there weren't any longs open."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Celine opens a long.
        market_deltas, wallet_deltas = hyperdrive_actions.calc_open_long(
            base_amount=FixedPoint("50_000_000.0"),
            market_state=self.hyperdrive.market_state,
            position_duration=self.hyperdrive.position_duration,
            pricing_model=self.hyperdrive.pricing_model,
            latest_checkpoint_time=self.hyperdrive.latest_checkpoint_time,
            spot_price=self.hyperdrive.spot_price,
        )
        self.hyperdrive.market_state.apply_delta(market_deltas)
        self.celine.wallet.update(wallet_deltas)

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, delta=self.APPROX_EQ)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * FixedPoint("2.0"))

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, delta=self.APPROX_EQ)

    def test_add_liquidity_with_short_immediately(self):
        """Test adding liquidity when there is a long short.  LP should still get the same number of
        shares as if there weren't any shorts open."""
        lp_supply_before = self.hyperdrive.market_state.lp_total_supply

        # Celine opens a short.
        market_deltas, wallet_deltas = self.hyperdrive.open_short(
            agent_wallet=self.celine.wallet,
            bond_amount=FixedPoint("50_000_000.0"),
        )

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure that the new LP receives the same amount of LP shares as the initializer.
        self.assertAlmostEqual(market_deltas.d_lp_total_supply, lp_supply_before, delta=self.APPROX_EQ)
        self.assertEqual(self.hyperdrive.market_state.lp_total_supply, lp_supply_before * FixedPoint("2.0"))

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, delta=self.APPROX_EQ)

    def test_add_liquidity_with_long_at_maturity(self):
        """Test adding liquidity with a long at maturity."""
        # Celine opens a long.
        market_deltas, wallet_deltas = self.hyperdrive.open_long(
            agent_wallet=self.celine.wallet,
            base_amount=FixedPoint("50_000_000.0"),
        )

        # Advance 1 year
        self.block_time.tick(FixedPoint("1.0"))

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(self.bob.wallet, self.contribution)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, delta=self.APPROX_EQ)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            agent_wallet=self.bob.wallet,
            lp_shares=self.bob.wallet.lp_tokens,
        )
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution, delta=self.APPROX_EQ)

    def test_add_liquidity_with_short_at_maturity(self):
        """Test adding liquidity with a short at maturity."""
        # Celine opens a short.
        market_deltas, wallet_deltas = self.hyperdrive.open_short(
            agent_wallet=self.celine.wallet,
            bond_amount=FixedPoint("50_000_000.0"),
        )

        # Advance 1 year
        self.block_time.tick(FixedPoint("1.0"))

        # Add liquidity with the same amount as the original contribution.
        market_deltas, wallet_deltas = self.hyperdrive.add_liquidity(
            agent_wallet=self.bob.wallet,
            bond_amount=self.contribution,
        )

        # Ensure that the agent lost money from their wallet
        self.assertAlmostEqual(wallet_deltas.balance.amount, -self.contribution, delta=self.APPROX_EQ)

        # Ensure that the contribution was transferred to Hyperdrive.
        self.assertEqual(market_deltas.d_base_asset, -wallet_deltas.balance.amount)

        # Ensure the pool APR is still approximately equal to the target APR.
        pool_apr = self.hyperdrive.pricing_model.calc_apr_from_reserves(
            self.hyperdrive.market_state, self.hyperdrive.position_duration
        )
        self.assertAlmostEqual(pool_apr, self.target_apr, delta=self.APPROX_EQ)

        # Ensure that if the new LP withdraws, they get their money back.
        market_deltas, wallet_deltas = self.hyperdrive.remove_liquidity(
            agent_wallet=self.bob.wallet,
            lp_shares=self.bob.wallet.lp_tokens,
        )
        # Test that Bob got their money back
        self.assertAlmostEqual(wallet_deltas.balance.amount, self.contribution, delta=self.APPROX_EQ)
