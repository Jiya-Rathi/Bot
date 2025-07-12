# 📬 Invoice Management & Reminder Bot (WhatsApp + AI)

A smart WhatsApp-based assistant that helps small and medium-sized businesses (SMBs) automate invoice tracking, reminders, forecasting, credit advice, and tax estimation. Built with IBM Watsonx, Granite LLM, and Twilio, the bot offers a conversational interface with AI-powered decision support and automation.

---

## ✨ Features

- 🔍 **Intent Detection + Smart Routing**  
  Classifies user messages and dispatches them to specialized modules:
  - `invoice_reminder` → Due date tracking, payment status, reminders  
  - `ledger` + `granite` → Cash flow forecasting and scenario simulation  
  - `loan` → Personalized credit and loan guidance  
  - `tax` → Income- and business-based tax estimation  

- 📸 **Image-Based Invoice Parsing** using Watsonx Vision  
- 🧠 **Granite 13B LLM Integration** for financial Q&A and explanations  
- 📅 **Automated Reminders** before and on invoice due dates  
- ✅ **Mark Invoices as Paid** or **Reschedule Payments**  
- 📊 **Weekly/Monthly Reports** on invoices, cash flow, and tax outlook  

---

## 💬 Sample Commands

- `"Upload invoice"` → Upload and parse invoice image  
- `"Show unpaid invoices this month"` → List pending payments  
- `"Forecast my cash flow for August"` → Run time-series prediction  
- `"Suggest credit options"` → Loan advice from the `loan` module  
- `"Estimate tax for this quarter"` → Smart tax calculations  
- `"Mark INV123 as DONE"` → Update payment status  
- `"Reschedule INV101 to next Friday"` → Change reminder  

---

## 🔮 Future Enhancements

- Dashboard with visual analytics  
- Multi-user support with secure login  
- Real-time Plaid integration for bank syncing  
- GST and business compliance alerts  
- Voice note parsing and reply  

---

## 🙌 Contribution

Have an idea or found a bug? Feel free to open an [issue](https://github.com/your-username/Finny-FinancialBot/issues) or submit a pull request!

---

## 📄 License

MIT License

