//+------------------------------------------------------------------+
//|                                    EA_Gradiente_Renko.mq5        |
//|                        Gradiente Linear com Preço Médio no Renko |
//|                                    Portado do backtest Python    |
//+------------------------------------------------------------------+
#property copyright "Renko Gradiente"
#property link      "https://github.com/lmteixeira17/Renko_Gradiente"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Arrays\ArrayLong.mqh>
#include <Arrays\ArrayDouble.mqh>

//--- Input Parameters
input group "=== Asset Settings ==="
input double   InpTickSize        = 5.0;           // Tick size (points)
input double   InpTickValue       = 0.20;          // Tick value (R$ per point)
input double   InpPointValue      = 1.0;           // Point value multiplier

input group "=== Renko Settings ==="
input int      InpRenkoR          = 25;            // Renko R value
input int      InpMinBricksSignal = 2;             // Min consecutive bricks for signal

input group "=== Gradient Settings ==="
input int      InpBaseQty         = 1;             // Base quantity per level
input double   InpPriceIncrement  = 100.0;         // Price increment between levels (pts)
input double   InpGainIncrement  = 50.0;         // Gain increment above avg price (pts)
input int      InpMaxLevels       = 3;             // Max levels (ML)
input bool     InpUseMartingale   = false;         // Use martingale (1-2-4-8...)

input group "=== Risk Management ==="
input double   InpStopLossPts     = 300.0;         // Stop loss in points
input double   InpDailyStopLoss   = 999999.0;      // Daily financial stop (R$)
input bool     InpTrailingStop    = false;         // Enable trailing stop
input double   InpTrailingValue   = 20.0;          // Trailing stop value (R$)
input bool     InpPreservationStop= false;         // Enable preservation stop
input int      InpPreservationLvls= 3;             // Preservation stop after N levels

input group "=== Filters ==="
input bool     InpUseMACD         = true;          // Use MACD filter
input bool     InpUse2MV          = true;          // Use 2MV filter

input group "=== Trading Hours ==="
input int      InpHourStart       = 10;            // Start hour (0-23)
input int      InpHourEnd         = 16;            // End hour (0-23)
input bool     InpCloseAtEndDay   = true;          // Close positions at end of day

input group "=== Execution ==="
input double   InpSlippagePts     = 2.0;           // Max slippage (points)
input double   InpCommissionPct   = 0.01;          // Commission % per side (0.01 = 1%)
input ulong    InpMagicNumber     = 171717;        // Magic number
input string   InpTradeComment    = "GradRenko";   // Trade comment

//--- Renko Brick Structure
struct RenkoBrick
{
   double open_price;
   double close_price;
   double high_price;
   double low_price;
   int    direction;     // +1 up, -1 down
   datetime start_time;
   datetime end_time;
   int      n_ticks;
};

//--- Level Structure
struct Level
{
   double price;
   int    qty;
   bool   filled;
};

//--- Trade State
enum ENUM_TRADE_DIRECTION
{
   DIR_FLAT = 0,
   DIR_LONG = 1,
   DIR_SHORT = -1
};

//--- Pending order tracking
struct PendingOrder
{
   ulong ticket;
   int   levelIdx;
   double price;
};

//--- Global Variables
CTrade         g_trade;
RenkoBrick     g_bricks[];
double         g_ema21[];
double         g_ema72[];
double         g_macdHist[];
string         g_2mvColors[];

Level          g_levels[];
int            g_levelCount = 0;
ENUM_TRADE_DIRECTION g_direction = DIR_FLAT;
int            g_positionQty = 0;
double         g_positionCost = 0.0;
double         g_avgPrice = 0.0;
double         g_targetPrice = 0.0;
double         g_stopPrice = 0.0;
int            g_currentLevelIdx = 0;
double         g_highestProfit = 0.0;
double         g_dailyPnL = 0.0;
double         g_totalPnL = 0.0;
double         g_peakEquity = 0.0;
double         g_maxDrawdown = 0.0;
int            g_nTrades = 0;
int            g_nWins = 0;
int            g_nLosses = 0;
double         g_grossProfit = 0.0;
double         g_grossLoss = 0.0;

//--- Renko state (for incremental building)
double         g_rCurrentOpen = 0;
double         g_rCurrentHigh = 0;
double         g_rCurrentLow = 0;
int            g_rDirection = 0;
datetime       g_rStartTime = 0;
int            g_rNTicks = 0;
double         g_brickSize = 0;
double         g_reversalSize = 0;

//--- Previous bar tracking
int            g_lastBrickCount = 0;
MqlTick        g_lastTick;
datetime       g_currentDay = 0;
bool           g_dayStopped = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Initialize trade object
   g_trade.SetExpertMagicNumber(InpMagicNumber);
   g_trade.SetDeviationInPoints((int)InpSlippagePts);
   g_trade.SetTypeFilling(ORDER_FILLING_FOK);
   g_trade.SetAsyncMode(false);
   
   //--- Calculate brick sizes
   g_brickSize = (InpRenkoR * InpTickSize) - InpTickSize;
   g_reversalSize = 2 * g_brickSize;
   
   Print("EA Gradiente Renko initialized");
   Print("  Brick size: ", g_brickSize, " pts (R=", InpRenkoR, ")");
   Print("  Reversal size: ", g_reversalSize, " pts");
   Print("  Max levels: ", InpMaxLevels, " | Martingale: ", InpUseMartingale);
   Print("  Stop loss: ", InpStopLossPts, " pts | Daily stop: R$", InpDailyStopLoss);
   
   //--- Get current tick to initialize
   SymbolInfoTick(_Symbol, g_lastTick);
   g_rCurrentOpen = g_lastTick.last;
   g_rCurrentHigh = g_lastTick.last;
   g_rCurrentLow  = g_lastTick.last;
   g_rStartTime   = TimeCurrent();
   g_rDirection   = 0;
   g_rNTicks      = 0;
   
   g_currentDay = TimeCurrent() / 86400 * 86400;
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("EA Gradiente Renko deinitialized. Final PnL: R$", DoubleToString(g_totalPnL, 2));
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   
   //--- Check new day
   datetime today = tick.time / 86400 * 86400;
   if(today != g_currentDay)
   {
      OnNewDay();
      g_currentDay = today;
   }
   
   //--- Check trading hours
   MqlDateTime dt;
   TimeToStruct(tick.time, dt);
   bool inTradingHours = (dt.hour >= InpHourStart && dt.hour < InpHourEnd);
   
   //--- Close positions at end of day
   if(InpCloseAtEndDay && dt.hour >= InpHourEnd && g_direction != DIR_FLAT)
   {
      CloseAllPositions("end_of_day");
      return;
   }
   
   //--- Check daily stop
   if(g_dayStopped)
      return;
   if(g_dailyPnL <= -InpDailyStopLoss)
   {
      g_dayStopped = true;
      if(g_direction != DIR_FLAT)
         CloseAllPositions("daily_stop");
      return;
   }
   
   //--- Update Renko bricks with this tick
   bool newBrick = UpdateRenko(tick);
   
   //--- If new brick formed, process signals
   int brickCount = ArraySize(g_bricks);
   if(newBrick && brickCount > g_lastBrickCount)
   {
      //--- Recalculate indicators on all bricks
      CalculateIndicators();
      
      //--- Check for entry signal on latest brick
      if(g_direction == DIR_FLAT && inTradingHours)
      {
         ENUM_TRADE_DIRECTION signal = CheckEntrySignal(brickCount - 1);
         if(signal != DIR_FLAT)
         {
            StartGradient(signal, g_bricks[brickCount - 1].close_price);
         }
      }
      
      g_lastBrickCount = brickCount;
   }
   
   //--- Check fills, targets, stops
   if(g_direction != DIR_FLAT)
   {
      ProcessPosition(tick);
   }
   
   g_lastTick = tick;
}

//+------------------------------------------------------------------+
//| OnNewDay - reset daily stats                                     |
//+------------------------------------------------------------------+
void OnNewDay()
{
   g_dailyPnL = 0.0;
   g_dayStopped = false;
   Print("New day started. Daily PnL reset.");
}

//+------------------------------------------------------------------+
//| Update Renko bricks incrementally                                |
//+------------------------------------------------------------------+
bool UpdateRenko(const MqlTick &tick)
{
   double price = tick.last;
   if(price == 0)
      price = (tick.bid + tick.ask) / 2.0;
   
   g_rNTicks++;
   if(price > g_rCurrentHigh) g_rCurrentHigh = price;
   if(price < g_rCurrentLow)  g_rCurrentLow  = price;
   
   bool newBrick = false;
   
   if(g_rDirection == 0)
   {
      if(price >= g_rCurrentOpen + g_brickSize)
      {
         g_rDirection = 1;
      }
      else if(price <= g_rCurrentOpen - g_brickSize)
      {
         g_rDirection = -1;
      }
      return false;
   }
   
   if(g_rDirection == 1)
   {
      if(price >= g_rCurrentOpen + g_brickSize)
      {
         // Close up brick
         AddBrick(g_rCurrentOpen, g_rCurrentOpen + g_brickSize, 
                  g_rCurrentHigh, g_rCurrentLow, 1, g_rStartTime, tick.time, g_rNTicks);
         g_rCurrentOpen = g_rCurrentOpen + g_brickSize;
         g_rCurrentHigh = price;
         g_rCurrentLow  = price;
         g_rStartTime   = tick.time;
         g_rNTicks      = 0;
         newBrick = true;
      }
      else if(price <= g_rCurrentOpen - g_reversalSize)
      {
         // Reversal to down
         AddBrick(g_rCurrentOpen, g_rCurrentOpen + g_brickSize,
                  g_rCurrentHigh, g_rCurrentLow, 1, g_rStartTime, tick.time, g_rNTicks);
         g_rCurrentOpen = g_rCurrentOpen - g_reversalSize + g_brickSize;
         g_rCurrentHigh = price;
         g_rCurrentLow  = price;
         g_rDirection   = -1;
         g_rStartTime   = tick.time;
         g_rNTicks      = 0;
         newBrick = true;
      }
   }
   else // g_rDirection == -1
   {
      if(price <= g_rCurrentOpen - g_brickSize)
      {
         // Close down brick
         AddBrick(g_rCurrentOpen, g_rCurrentOpen - g_brickSize,
                  g_rCurrentHigh, g_rCurrentLow, -1, g_rStartTime, tick.time, g_rNTicks);
         g_rCurrentOpen = g_rCurrentOpen - g_brickSize;
         g_rCurrentHigh = price;
         g_rCurrentLow  = price;
         g_rStartTime   = tick.time;
         g_rNTicks      = 0;
         newBrick = true;
      }
      else if(price >= g_rCurrentOpen + g_reversalSize)
      {
         // Reversal to up
         AddBrick(g_rCurrentOpen, g_rCurrentOpen - g_brickSize,
                  g_rCurrentHigh, g_rCurrentLow, -1, g_rStartTime, tick.time, g_rNTicks);
         g_rCurrentOpen = g_rCurrentOpen + g_reversalSize - g_brickSize;
         g_rCurrentHigh = price;
         g_rCurrentLow  = price;
         g_rDirection   = 1;
         g_rStartTime   = tick.time;
         g_rNTicks      = 0;
         newBrick = true;
      }
   }
   
   return newBrick;
}

//+------------------------------------------------------------------+
//| Add brick to array                                               |
//+------------------------------------------------------------------+
void AddBrick(double open_p, double close_p, double high_p, double low_p,
              int dir, datetime start_t, datetime end_t, int n_ticks)
{
   int n = ArraySize(g_bricks);
   ArrayResize(g_bricks, n + 1);
   g_bricks[n].open_price  = open_p;
   g_bricks[n].close_price = close_p;
   g_bricks[n].high_price  = high_p;
   g_bricks[n].low_price   = low_p;
   g_bricks[n].direction   = dir;
   g_bricks[n].start_time  = start_t;
   g_bricks[n].end_time    = end_t;
   g_bricks[n].n_ticks     = n_ticks;
}

//+------------------------------------------------------------------+
//| Calculate EMA, MACD, 2MV on brick closes                         |
//+------------------------------------------------------------------+
void CalculateIndicators()
{
   int n = ArraySize(g_bricks);
   if(n < 73) return;
   
   //--- Extract close prices
   double closes[];
   ArrayResize(closes, n);
   for(int i = 0; i < n; i++)
      closes[i] = g_bricks[i].close_price;
   
   //--- Calculate EMAs
   ArrayResize(g_ema21, n);
   ArrayResize(g_ema72, n);
   CalculateEMA(closes, g_ema21, 21);
   CalculateEMA(closes, g_ema72, 72);
   
   //--- Calculate MACD
   double macdLine[];
   ArrayResize(macdLine, n);
   for(int i = 0; i < n; i++)
      macdLine[i] = g_ema21[i] - g_ema72[i];
   
   double signalLine[];
   ArrayResize(signalLine, n);
   CalculateEMA(macdLine, signalLine, 9);
   
   ArrayResize(g_macdHist, n);
   for(int i = 0; i < n; i++)
      g_macdHist[i] = macdLine[i] - signalLine[i];
   
   //--- Calculate 2MV colors
   ArrayResize(g_2mvColors, n);
   for(int i = 0; i < n; i++)
   {
      g_2mvColors[i] = Get2MVColor(closes, i);
   }
}

//+------------------------------------------------------------------+
//| Calculate EMA                                                    |
//+------------------------------------------------------------------+
void CalculateEMA(const double &src[], double &dst[], int period)
{
   int n = ArraySize(src);
   if(n == 0) return;
   
   double alpha = 2.0 / (period + 1);
   dst[0] = src[0];
   for(int i = 1; i < n; i++)
   {
      dst[i] = src[i] * alpha + dst[i-1] * (1.0 - alpha);
   }
}

//+------------------------------------------------------------------+
//| Get 2MV Color                                                    |
//+------------------------------------------------------------------+
string Get2MVColor(const double &prices[], int idx)
{
   if(idx < 1) return "neutral";
   
   double price = prices[idx];
   double ef = g_ema21[idx];
   double es = g_ema72[idx];
   double slopeFast = g_ema21[idx] - g_ema21[idx - 1];
   double slopeSlow = g_ema72[idx] - g_ema72[idx - 1];
   
   if(price > ef && ef > es && slopeFast > 0 && slopeSlow > 0)
      return "green";
   if(price < ef && ef < es && slopeFast < 0 && slopeSlow < 0)
      return "red";
   
   return "neutral";
}

//+------------------------------------------------------------------+
//| Check Entry Signal                                               |
//+------------------------------------------------------------------+
ENUM_TRADE_DIRECTION CheckEntrySignal(int brickIdx)
{
   if(brickIdx < 1) return DIR_FLAT;
   if(ArraySize(g_ema21) == 0) return DIR_FLAT; // Indicators not ready
   
   RenkoBrick curr = g_bricks[brickIdx];
   RenkoBrick prev = g_bricks[brickIdx - 1];
   
   //--- Condition 1: current brick direction
   ENUM_TRADE_DIRECTION side = DIR_FLAT;
   if(curr.direction == 1) side = DIR_LONG;
   else if(curr.direction == -1) side = DIR_SHORT;
   else return DIR_FLAT;
   
   //--- Condition 2: 2MV color
   if(InpUse2MV)
   {
      string color = g_2mvColors[brickIdx];
      if(side == DIR_LONG && color != "green") return DIR_FLAT;
      if(side == DIR_SHORT && color != "red") return DIR_FLAT;
   }
   
   //--- Condition 3: MACD histogram
   if(InpUseMACD)
   {
      double hist = g_macdHist[brickIdx];
      if(side == DIR_LONG && hist <= 0) return DIR_FLAT;
      if(side == DIR_SHORT && hist >= 0) return DIR_FLAT;
   }
   
   //--- Condition 4: trigger (pullback or continuation)
   if(prev.direction != curr.direction)
   {
      // Pullback entry
      return side;
   }
   else
   {
      // Count consecutive bricks in same direction
      int count = 1;
      for(int i = brickIdx - 1; i >= 0; i--)
      {
         if(g_bricks[i].direction == curr.direction)
            count++;
         else
            break;
      }
      if(count >= InpMinBricksSignal)
         return side;
   }
   
   return DIR_FLAT;
}

//+------------------------------------------------------------------+
//| Start Gradient                                                   |
//+------------------------------------------------------------------+
void StartGradient(ENUM_TRADE_DIRECTION dir, double anchorPrice)
{
   //--- Reset position state
   ResetPosition();
   g_direction = dir;
   
   //--- Build levels
   g_levelCount = InpMaxLevels;
   ArrayResize(g_levels, g_levelCount);
   
   for(int i = 0; i < g_levelCount; i++)
   {
      if(dir == DIR_LONG)
         g_levels[i].price = anchorPrice - i * InpPriceIncrement;
      else
         g_levels[i].price = anchorPrice + i * InpPriceIncrement;
      
      if(InpUseMartingale)
         g_levels[i].qty = InpBaseQty * (int)MathPow(2, i);
      else
         g_levels[i].qty = InpBaseQty;
      
      g_levels[i].filled = false;
   }
   
   g_currentLevelIdx = 0;
   
   //--- Place initial limit orders (first 5 or max_levels)
   int nInitial = MathMin(5, g_levelCount);
   for(int i = 0; i < nInitial; i++)
   {
      PlaceLimitOrder(i);
   }
   
   Print("Gradient started: ", (dir == DIR_LONG ? "LONG" : "SHORT"), 
         " anchor=", anchorPrice, " levels=", g_levelCount);
}

//+------------------------------------------------------------------+
//| Place Limit Order                                                |
//+------------------------------------------------------------------+
void PlaceLimitOrder(int levelIdx)
{
   if(levelIdx >= g_levelCount) return;
   if(g_levels[levelIdx].filled) return;
   
   double price = g_levels[levelIdx].price;
   int qty = g_levels[levelIdx].qty;
   ENUM_ORDER_TYPE orderType;
   
   if(g_direction == DIR_LONG)
      orderType = ORDER_TYPE_BUY_LIMIT;
   else
      orderType = ORDER_TYPE_SELL_LIMIT;
   
   //--- Adjust price to tick size
   price = NormalizeDouble(price, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS));
   
   //--- Check if price is valid for limit order
   MqlTick tick;
   SymbolInfoTick(_Symbol, tick);
   
   if(g_direction == DIR_LONG && price >= tick.ask)
   {
      // Price already above market, execute as market order
      g_trade.Buy(qty, _Symbol, tick.ask, 0, 0, InpTradeComment);
      OnLevelFilled(levelIdx, tick.ask);
      return;
   }
   if(g_direction == DIR_SHORT && price <= tick.bid)
   {
      // Price already below market, execute as market order
      g_trade.Sell(qty, _Symbol, tick.bid, 0, 0, InpTradeComment);
      OnLevelFilled(levelIdx, tick.bid);
      return;
   }
   
   //--- Place limit order
   if(!g_trade.OrderOpen(_Symbol, orderType, qty, 0, price, 0, 0, 
                         ORDER_TIME_GTC, 0, InpTradeComment))
   {
      Print("Failed to place limit order at ", price, ": ", GetLastError());
   }
   else
   {
      ulong ticket = g_trade.ResultOrder();
      AddPendingOrder(ticket, levelIdx, price);
      Print("Limit order placed: ", (orderType == ORDER_TYPE_BUY_LIMIT ? "BUY" : "SELL"),
            " ", qty, " @ ", price, " ticket=", ticket);
   }
}

//+------------------------------------------------------------------+
//| Process Position - check fills, targets, stops                   |
//+------------------------------------------------------------------+
void ProcessPosition(const MqlTick &tick)
{
   double price = tick.last;
   if(price == 0)
      price = (tick.bid + tick.ask) / 2.0;
   
   //--- Check level fills
   for(int i = 0; i < g_levelCount; i++)
   {
      if(g_levels[i].filled) continue;
      
      if(g_direction == DIR_LONG && price <= g_levels[i].price)
      {
         OnLevelFilled(i, price);
      }
      else if(g_direction == DIR_SHORT && price >= g_levels[i].price)
      {
         OnLevelFilled(i, price);
      }
   }
   
   if(g_positionQty == 0) return;
   
   //--- Calculate unrealized PnL
   double unreal = 0;
   if(g_direction == DIR_LONG)
      unreal = (price - g_avgPrice) * g_positionQty * InpTickValue * InpPointValue;
   else
      unreal = (g_avgPrice - price) * g_positionQty * InpTickValue * InpPointValue;
   
   //--- Track highest profit for trailing stop
   if(unreal > g_highestProfit)
      g_highestProfit = unreal;
   
   //--- Check target hit
   bool hitTarget = false;
   if(g_direction == DIR_LONG && price >= g_targetPrice)
      hitTarget = true;
   else if(g_direction == DIR_SHORT && price <= g_targetPrice)
      hitTarget = true;
   
   if(hitTarget)
   {
      CloseAllPositions("target");
      return;
   }
   
   //--- Check stop loss
   bool hitStop = false;
   if(g_direction == DIR_LONG && price <= g_stopPrice)
      hitStop = true;
   else if(g_direction == DIR_SHORT && price >= g_stopPrice)
      hitStop = true;
   
   if(hitStop)
   {
      CloseAllPositions("stop");
      return;
   }
   
   //--- Check trailing stop
   if(InpTrailingStop && g_highestProfit > InpTrailingValue)
   {
      double trailPrice;
      if(g_direction == DIR_LONG)
         trailPrice = g_avgPrice + (g_highestProfit - InpTrailingValue) / (g_positionQty * InpTickValue * InpPointValue);
      else
         trailPrice = g_avgPrice - (g_highestProfit - InpTrailingValue) / (g_positionQty * InpTickValue * InpPointValue);
      
      if(g_direction == DIR_LONG && price <= trailPrice)
      {
         CloseAllPositions("trailing_stop");
         return;
      }
      else if(g_direction == DIR_SHORT && price >= trailPrice)
      {
         CloseAllPositions("trailing_stop");
         return;
      }
   }
   
   //--- Check preservation stop
   if(InpPreservationStop && g_currentLevelIdx >= InpPreservationLvls)
   {
      // Move stop to breakeven + small profit after N levels
      double newStop;
      if(g_direction == DIR_LONG)
         newStop = g_avgPrice + InpGainIncrement * 0.5;
      else
         newStop = g_avgPrice - InpGainIncrement * 0.5;
      
      // Only move stop if it improves our position
      if(g_direction == DIR_LONG && newStop > g_stopPrice)
         g_stopPrice = newStop;
      else if(g_direction == DIR_SHORT && newStop < g_stopPrice)
         g_stopPrice = newStop;
   }
}

//+------------------------------------------------------------------+
//| On Level Filled                                                  |
//+------------------------------------------------------------------+
void OnLevelFilled(int levelIdx, double fillPrice)
{
   g_levels[levelIdx].filled = true;
   g_currentLevelIdx = MathMax(g_currentLevelIdx, levelIdx + 1);
   
   //--- Update average price
   g_positionCost += fillPrice * g_levels[levelIdx].qty;
   g_positionQty += g_levels[levelIdx].qty;
   g_avgPrice = g_positionCost / g_positionQty;
   
   //--- Update target and stop
   if(g_direction == DIR_LONG)
   {
      g_targetPrice = g_avgPrice + InpGainIncrement;
      g_stopPrice = g_avgPrice - InpStopLossPts;
   }
   else
   {
      g_targetPrice = g_avgPrice - InpGainIncrement;
      g_stopPrice = g_avgPrice + InpStopLossPts;
   }
   
   //--- Place next level if exists
   int nextLevel = levelIdx + 5; // Keep 5 levels ahead
   if(nextLevel < g_levelCount && !g_levels[nextLevel].filled)
   {
      PlaceLimitOrder(nextLevel);
   }
   
   Print("Level ", levelIdx, " filled @ ", fillPrice, " qty=", g_levels[levelIdx].qty,
         " avg=", g_avgPrice, " target=", g_targetPrice, " stop=", g_stopPrice);
}

//+------------------------------------------------------------------+
//| Close All Positions                                              |
//+------------------------------------------------------------------+
void CloseAllPositions(string reason)
{
   if(g_positionQty == 0)
   {
      ResetPosition();
      return;
   }
   
   MqlTick tick;
   SymbolInfoTick(_Symbol, tick);
   double exitPrice = (g_direction == DIR_LONG) ? tick.bid : tick.ask;
   
   //--- Calculate PnL
   double pnl;
   if(g_direction == DIR_LONG)
      pnl = (exitPrice - g_avgPrice) * g_positionQty * InpTickValue * InpPointValue;
   else
      pnl = (g_avgPrice - exitPrice) * g_positionQty * InpTickValue * InpPointValue;
   
   //--- Subtract commission
   double turnover = exitPrice * g_positionQty;
   double commission = turnover * InpCommissionPct / 100.0;
   pnl -= commission;
   
   //--- Close all positions
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && 
         PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
      {
         g_trade.PositionClose(ticket);
      }
   }
   
   //--- Cancel pending orders
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         OrderGetInteger(ORDER_MAGIC) == InpMagicNumber)
      {
         g_trade.OrderDelete(ticket);
      }
   }
   
   //--- Update stats
   UpdateStats(pnl, reason, exitPrice);
   
   //--- Reset position
   ResetPosition();
   
   Print("Position closed (", reason, ") PnL=R$", DoubleToString(pnl, 2),
         " exit=", exitPrice, " qty=", g_positionQty);
}

//+------------------------------------------------------------------+
//| Update Statistics                                                |
//+------------------------------------------------------------------+
void UpdateStats(double pnl, string reason, double exitPrice)
{
   g_nTrades++;
   g_totalPnL += pnl;
   g_dailyPnL += pnl;
   
   if(pnl > 0)
   {
      g_nWins++;
      g_grossProfit += pnl;
   }
   else
   {
      g_nLosses++;
      g_grossLoss += pnl;
   }
   
   //--- Update drawdown
   if(g_totalPnL > g_peakEquity)
      g_peakEquity = g_totalPnL;
   double dd = g_peakEquity - g_totalPnL;
   if(dd > g_maxDrawdown)
      g_maxDrawdown = dd;
   
   //--- Alert on stop loss
   if(reason == "stop" || reason == "trailing_stop")
   {
      Alert("STOP HIT! PnL=R$", DoubleToString(pnl, 2), " Exit=", exitPrice);
   }
}

//+------------------------------------------------------------------+
//| Reset Position                                                   |
//+------------------------------------------------------------------+
void ResetPosition()
{
   //--- Cancel all pending orders
   for(int i = ArraySize(g_pendingOrders) - 1; i >= 0; i--)
   {
      g_trade.OrderDelete(g_pendingOrders[i].ticket);
   }
   ArrayResize(g_pendingOrders, 0);
   g_pendingCount = 0;
   
   g_direction = DIR_FLAT;
   ArrayResize(g_levels, 0);
   g_levelCount = 0;
   g_positionQty = 0;
   g_positionCost = 0.0;
   g_avgPrice = 0.0;
   g_targetPrice = 0.0;
   g_stopPrice = 0.0;
   g_currentLevelIdx = 0;
   g_highestProfit = 0.0;
}

//+------------------------------------------------------------------+
//| Add Pending Order                                                |
//+------------------------------------------------------------------+
void AddPendingOrder(ulong ticket, int levelIdx, double price)
{
   int n = ArraySize(g_pendingOrders);
   ArrayResize(g_pendingOrders, n + 1);
   g_pendingOrders[n].ticket = ticket;
   g_pendingOrders[n].levelIdx = levelIdx;
   g_pendingOrders[n].price = price;
   g_pendingCount++;
}

//+------------------------------------------------------------------+
//| Remove Pending Order                                             |
//+------------------------------------------------------------------+
void RemovePendingOrder(ulong ticket)
{
   int n = ArraySize(g_pendingOrders);
   for(int i = 0; i < n; i++)
   {
      if(g_pendingOrders[i].ticket == ticket)
      {
         for(int j = i; j < n - 1; j++)
            g_pendingOrders[j] = g_pendingOrders[j + 1];
         ArrayResize(g_pendingOrders, n - 1);
         g_pendingCount--;
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| Find Pending Order by Ticket                                     |
//+------------------------------------------------------------------+
int FindPendingOrder(ulong ticket)
{
   int n = ArraySize(g_pendingOrders);
   for(int i = 0; i < n; i++)
   {
      if(g_pendingOrders[i].ticket == ticket)
         return i;
   }
   return -1;
}

//+------------------------------------------------------------------+
//| OnTrade - handle order fills                                     |
//+------------------------------------------------------------------+
void OnTrade()
{
   //--- Check for filled pending orders
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      ulong ticket = OrderGetTicket(i);
      if(OrderGetString(ORDER_SYMBOL) != _Symbol) continue;
      if(OrderGetInteger(ORDER_MAGIC) != InpMagicNumber) continue;
      
      ENUM_ORDER_STATE state = (ENUM_ORDER_STATE)OrderGetInteger(ORDER_STATE);
      if(state == ORDER_STATE_FILLED || state == ORDER_STATE_PARTIAL)
      {
         int idx = FindPendingOrder(ticket);
         if(idx >= 0)
         {
            int levelIdx = g_pendingOrders[idx].levelIdx;
            double fillPrice = OrderGetDouble(ORDER_PRICE_CURRENT);
            RemovePendingOrder(ticket);
            
            if(levelIdx >= 0 && levelIdx < g_levelCount && !g_levels[levelIdx].filled)
            {
               OnLevelFilled(levelIdx, fillPrice);
            }
         }
      }
   }
   
   //--- Check for new positions from market orders
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      
      // Position exists but no gradient active - something is wrong
      if(g_direction == DIR_FLAT)
      {
         Print("WARNING: Orphan position detected. Closing.");
         g_trade.PositionClose(ticket);
      }
   }
}

//+------------------------------------------------------------------+
//| Print Statistics                                                 |
//+------------------------------------------------------------------+
void PrintStats()
{
   double wr = (g_nTrades > 0) ? (double)g_nWins / g_nTrades * 100.0 : 0.0;
   double pf = (g_grossLoss < 0) ? MathAbs(g_grossProfit / g_grossLoss) : 0.0;
   
   Print("=== EA STATISTICS ===");
   Print("Trades: ", g_nTrades, " (W:", g_nWins, " L:", g_nLosses, ")");
   Print("Win Rate: ", DoubleToString(wr, 1), "%");
   Print("Profit Factor: ", DoubleToString(pf, 2));
   Print("Net PnL: R$", DoubleToString(g_totalPnL, 2));
   Print("Max Drawdown: R$", DoubleToString(g_maxDrawdown, 2));
   Print("Daily PnL: R$", DoubleToString(g_dailyPnL, 2));
   Print("=====================");
}

//+------------------------------------------------------------------+
//| OnTimer - print stats periodically                               |
//+------------------------------------------------------------------+
void OnTimer()
{
   PrintStats();
}

//+------------------------------------------------------------------+
//| OnTester - optimization criterion                                |
//+------------------------------------------------------------------+
double OnTester()
{
   //--- Custom optimization criterion: Return / Drawdown ratio
   double dd = g_maxDrawdown;
   if(dd <= 0) dd = 1.0;
   
   double ret_dd = g_totalPnL / dd;
   double wr = (g_nTrades > 0) ? (double)g_nWins / g_nTrades * 100.0 : 0.0;
   double pf = (g_grossLoss < 0) ? MathAbs(g_grossProfit / g_grossLoss) : 0.0;
   
   //--- Composite score: favor high return/DD, good PF, and decent WR
   double score = ret_dd * MathSqrt(pf + 0.01) * (wr / 100.0 + 0.1);
   
   Print("OnTester: PnL=R$", DoubleToString(g_totalPnL, 2),
         " DD=R$", DoubleToString(g_maxDrawdown, 2),
         " R/DD=", DoubleToString(ret_dd, 2),
         " Score=", DoubleToString(score, 4));
   
   return score;
}
