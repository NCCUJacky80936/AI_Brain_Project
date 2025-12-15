# 高階系統設計文件 (High-Level System Design) - 歡樂世界收費計算器

-----

## 1\. 系統架構 (System Architecture)

本系統採用經典的三層式架構 (3-Tier Architecture)，確保關注點分離 (Separation of Concerns)，提高程式碼的可維護性與未來擴充性。

  - **Presentation Layer (使用者互動層)**

      - **職責**: 負責所有與使用者（櫃檯人員）的互動。包含顯示選單、接收使用者輸入、格式化並呈現計費結果、以及顯示錯誤訊息。
      - **對應實作**: `Program.cs` 類別，為 Console 應用程式的進入點與主迴圈。

  - **Business Logic Layer (BLL - 商業邏輯層)**

      - **職責**: 執行核心的業務規則與運算。包含根據日期時間判斷費率、計算各項設施費用、應用優惠（如保齡球買五送一）、驗證業務邏輯（如球桿租借數量限制），並彙總總金額。
      - **對應實作**: `BillingService.cs` 類別，封裝所有計費相關的商業邏輯。

  - **Data Access / Configuration Layer (資料設定層)**

      - **職責**: 提供唯讀的靜態設定資料。在本系統中，此層負責管理所有硬編碼 (Hard-coded) 的設施費率、租借物價格、以及國定假日清單。它將資料以結構化的方式提供給商業邏輯層使用。
      - **對應實作**: `RateProvider.cs` 類別。

## 2\. 系統資料設計 (System Data Design)

系統核心資料模型將使用 C\# `record` 型別定義，以確保資料的不可變性 (Immutability)，提升系統的穩定性。

```csharp
// --- Enums ---

// 設施類型
public enum FacilityType 
{
    Bowling,
    Billiards,
    Darts
}

// 日期類型
public enum DateType 
{
    Weekday,
    Holiday
}

// --- Request Models ---

/// <summary>
/// 代表一筆完整的計費請求，可包含多項設施。
/// </summary>
public record BillingRequest(
    DateTime TransactionDateTime,
    List<FacilityRequestBase> FacilityRequests
);

/// <summary>
/// 設施計費請求的基底型別。
/// </summary>
public abstract record FacilityRequestBase(FacilityType Facility);

/// <summary>
/// 保齡球計費請求的詳細資料。
/// </summary>
public record BowlingRequest(
    int ParticipantCount,
    int GamesCount,
    int ShoeRentalCount
) : FacilityRequestBase(FacilityType.Bowling);

/// <summary>
/// 撞球計費請求的詳細資料。
/// </summary>
public record BilliardsRequest(
    int ParticipantCount,
    decimal PlayHours,
    int PremiumCueRentalCount,
    int StandardCueRentalCount
) : FacilityRequestBase(FacilityType.Billiards);

/// <summary>
/// 飛鏢計費請求的詳細資料。
/// </summary>
public record DartsRequest(
    int GamesCount,
    bool IsRentingDarts
) : FacilityRequestBase(FacilityType.Darts);


// --- Result Models ---

/// <summary>
/// 代表一筆計算完成的計費結果。
/// </summary>
public record BillingResult(
    List<ChargeItem> ChargeItems,
    decimal TotalPaymentAmount
);

/// <summary>
/// 代表費用明細中的單一項目。
/// </summary>
public record ChargeItem(
    string Description,
    decimal UnitPrice,
    decimal Quantity,
    decimal Subtotal,
    string? Note = null // 用於標示優惠等資訊
);


// --- Configuration/Rate Models ---

/// <summary>
/// 代表單一設施在特定條件下的費率資訊。
/// </summary>
public record RateInfo(
    FacilityType Facility,
    DateType DateType,
    TimeSpan StartTime,
    TimeSpan EndTime,
    decimal UnitPrice,
    string UnitDescription // "每局" 或 "每小時"
);

/// <summary>
/// 代表租借物的價格資訊。
/// </summary>
public record RentalRateInfo(
    string ItemName,
    decimal UnitPrice
);

```

## 3\. 系統流程 (System Flow)

系統從啟動到完成計費的完整高階流程如下：

1.  **系統啟動**：`Program.Main()` 進入主應用程式迴圈。
2.  **顯示主選單**：向使用者顯示可選擇的設施（保齡球、撞球、飛鏢）及離開選項。
3.  **接收設施選擇**：使用者可選擇一或多項設施進行計費。
4.  **建立計費請求容器**：初始化一個 `List<FacilityRequestBase>` 用於存放本次交易的所有設施請求。
5.  **依序收集各項設施資訊**：
      - **For each** 使用者選擇的設施：
          - 呼叫對應的輸入函式 (e.g., `GetBowlingInputs()`)。
          - 在函式內部，提示使用者輸入所需參數（如：人數、局數/時數、租借物數量）。
          - 使用 `InputValidator` 驗證每一次輸入（如：是否為正整數）。
          - 若輸入無效，顯示錯誤訊息並要求重新輸入，直到有效為止。
          - 將驗證後的資料建立成對應的 Request 物件（`BowlingRequest`, `BilliardsRequest`...）。
          - 將建立的 Request 物件加入步驟 4 的 List 中。
6.  **組合完整計費請求**：
      - 取得當前系統時間作為 `TransactionDateTime`。
      - 建立一個 `BillingRequest` 物件，將 `TransactionDateTime` 和包含所有設施請求的 List 傳入。
7.  **執行計費**：
      - 實例化 `BillingService`。
      - 呼叫 `billingService.CalculateTotal(billingRequest)`，傳入完整的計費請求。
8.  **內部計費邏輯 (BillingService)**：
      - 服務接收到 `BillingRequest`。
      - 根據 `TransactionDateTime`，向 `RateProvider` 查詢當日屬於 `Weekday` 或 `Holiday`。
      - **For each** `facilityRequest` in `billingRequest.FacilityRequests`:
          - 向 `RateProvider` 取得該設施在該時段的 `RateInfo`。
          - 根據設施類型，套用特定計費規則：
              - **保齡球**：計算局數費用，檢查並套用「買五送一」優惠，計算球鞋租借費。
              - **撞球**：將遊玩時數無條件進位至整數，計算時數費用，計算球桿租借費。
              - **飛鏢**：計算局數費用，計算飛鏢租借費。
          - 將計算出的費用轉換成一或多個 `ChargeItem` 物件。
      - 加總所有 `ChargeItem` 的 `Subtotal`，得到 `TotalPaymentAmount`。
      - 建立並回傳 `BillingResult` 物件。
9.  **顯示結果**：
      - `Program` 層接收到 `BillingResult`。
      - 格式化輸出，清晰地條列顯示每一個 `ChargeItem` 的明細（描述、單價、數量、小計、備註）。
      - 顯示最終的 `TotalPaymentAmount` (應付總額)。
10. **返回主選單**：流程回到步驟 2，等待下一次計費。

## 4\. 功能設計 (Function Design)

系統功能將被拆解為以下幾個核心類別與其主要方法。

### `Program`

  - **職責**: Console UI 互動與流程控制。
  - **核心方法**:
      - `static void Main(string[] args)`: 應用程式進入點，包含主迴圈，協調呼叫其他方法。
      - `private static void HandleBillingProcess()`: 處理單次計費的完整流程，從選擇設施到顯示結果。
      - `private static List<FacilityRequestBase> GetFacilitySelections()`: 顯示設施選單並收集使用者選擇。
      - `private static BowlingRequest GetBowlingInputs()`: 提示並收集保齡球計費所需的所有參數。
      - `private static BilliardsRequest GetBilliardsInputs()`: 提示並收集撞球計費所需的所有參數。
      - `private static DartsRequest GetDartsInputs()`: 提示並收集飛鏢計費所需的所有參數。
      - `private static void DisplayBillingResult(BillingResult result)`: 將 `BillingResult` 物件格式化並輸出至 Console。

### `BillingService`

  - **職責**: 封裝所有核心計費商業邏輯。
  - **核心方法**:
      - `public BillingResult CalculateTotal(BillingRequest request)`: 主要公開方法。接收完整的計費請求，回傳計算後的結果。此方法將協調內部私有方法完成計算。
      - `private ChargeItem CalculateBowlingFee(BowlingRequest request, RateInfo rate)`: 計算保齡球的設施費用與租借費用，並處理優惠邏輯。
      - `private ChargeItem CalculateBilliardsFee(BilliardsRequest request, RateInfo rate)`: 計算撞球的設施費用與租借費用，並處理時數進位邏輯。
      - `private ChargeItem CalculateDartsFee(DartsRequest request, RateInfo rate)`: 計算飛鏢的設施費用與租借費用。

### `RateProvider`

  - **職責**: 提供所有靜態的費率與假日資料。
  - **核心方法**:
      - `public RateInfo GetFacilityRate(FacilityType facility, DateTime transactionTime)`: 根據設施類型與交易時間，回傳對應的費率資訊 `RateInfo`。
      - `public RentalRateInfo GetRentalRate(string itemName)`: 根據租借物名稱回傳其價格。
      - `public DateType GetDateType(DateTime transactionTime)`: 判斷給定時間是屬於平日還是假日（包含週五 17:00 後的規則）。
      - `private bool IsHoliday(DateTime date)`: 檢查給定日期是否在硬編碼的國定假日清單中。

### `InputValidator`

  - **職責**: 提供可重用的使用者輸入驗證功能。
  - **核心方法**:
      - `public static int GetPositiveInt(string prompt)`: 提示使用者輸入，並確保回傳一個正整數。
      - `public static decimal GetPositiveDecimal(string prompt)`: 提示使用者輸入，並確保回傳一個正數（可為小數）。
      - `public static bool GetYesNo(string prompt)`: 提示使用者輸入 (y/n)，並回傳布林值。
      - `public static void ValidateBilliardsCues(int participantCount, int premiumCues, int standardCues)`: 驗證撞球球桿總數是否超過參與人數，若超過則拋出例外。

## 5\. 驗收條件

每個功能需求須至少通過一組結構化測試案例，以確保系統操作正確與邏輯嚴謹。

  - **範例一：保齡球**

      - 條件：平日 16:00，2人，購買5局，租鞋1人
      - 預期：費用 = (60*5) + (20*1) = 320元，系統明顯顯示贈送1局

  - **範例二：撞球**

      - 條件：週日13:00，1人，0.5小時，租普通球桿1支
      - 預期：費用 = 240元（1小時計）+ 100元（球桿）= 340元

  - **範例三：飛鏢**

      - 條件：國定假日15:00，3局，租借飛鏢
      - 預期：費用 = 50\*3 + 20 = 170元

  - **範例四：撞球球桿超過人數限制**

      - 條件：2人，租高級2支+普通1支
      - 預期：系統阻止輸入，並顯示超過限制錯誤

  - **範例五：保齡球違反數字輸入**

      - 條件：遊玩人數輸入 -3
      - 預期：系統提示錯誤，要求重新輸入

  - **範例六：跨時段計價**

      - 條件：週五 22:55 開始保齡球，買3局
      - 預期：全部以假日價格（85元/局）計算

  - **範例七：多項設施合併計費**

      - 條件：平日14:20，1人玩保齡球（2局，租鞋1人）、撞球（1小時，租普通球桿1支）、飛鏢（2局，租借飛鏢）
      - 預期：費用 = 保齡球(60*2+20*1) + 撞球(200*1+100*1) + 飛鏢(50\*2+20) = 560元