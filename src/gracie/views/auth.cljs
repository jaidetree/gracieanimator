(ns gracie.views.auth)

(defn view
  [req {:keys []}]
  [:div#login-page
   [:form#login-form.max-w-xl.m-auto
    {:method "POST"
     :action "/.netlify/functions/auth"}
    [:h2.text-center.mb-4
     "This page is password protected"]
    [:div.md:flex.md:flex-row.gap-2
     [:input.bg-black.bg-opacity-20.px-4.py-2.text-xl.text-white.w-full.rounded-sm.placeholder:text-white.placehoder:text-opacity-75
      {:type "password"
       :placeholder "password"
       :name "password"}]
     [:button.text-white.border-white.border.rounded-sm.px-4.py-2.text-sm
      {:type "submit"
       :name "submit_btn"}
      "Login"]]
    [:div#login-form-status.text-center.py-4]]
   [:script
    {:type "application/x-scittle"
     :src "/cljs/auth.cljs"}]])
